#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent, seeded public-editor checks using Python's TOML semantic oracle.

The runner protocol is:
    RUNNER set|remove SOURCE_FILE VALUE_FILE OUTPUT_FILE KEY_COMPONENT...
Successful calls write OUTPUT_FILE; rejected calls return nonzero without
creating it. No editor implementation or source-span scanner is reproduced here.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import random
import subprocess
import tempfile
import tomllib


LIMIT = 1_048_576
SEED = 20261104


def key(value):
    """Always-quoted keys deliberately distinguish literal dots from paths."""
    return json.dumps(value, ensure_ascii=False)


def dotted(parts):
    return '.'.join(key(part) for part in parts)


def parse(source):
    return tomllib.loads(source.decode('utf-8'))


def parent(model, path, create=False):
    node = model
    for component in path[:-1]:
        if create:
            node = node.setdefault(component, {})
        else:
            node = node[component]
    return node


def same(actual, expected):
    """Avoid Python's bool==int and signed-zero equality hiding a wrong edit."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            same(actual[name], value) for name, value in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(map(same, actual, expected))
    if isinstance(expected, float) and expected == 0.0:
        return actual == 0.0 and math.copysign(1.0, actual) == math.copysign(1.0, expected)
    return actual == expected


class Campaign:
    def __init__(self, runner, directory):
        self.runner = runner
        self.directory = directory
        self.calls = 0

    def call(self, mode, source, path, value=b'', *, rejected=False, expected=None):
        self.calls += 1
        source_file = self.directory / 'source.toml'
        value_file = self.directory / 'value.toml'
        output_file = self.directory / 'output.toml'
        source_file.write_bytes(source)
        value_file.write_bytes(value)
        output_file.unlink(missing_ok=True)
        command = [str(self.runner), mode, str(source_file), str(value_file),
                   str(output_file), *path]
        result = subprocess.run(command, capture_output=True, timeout=20)
        context = (f'call {self.calls}: mode={mode}, path={path!r}, '
                   f'source={source[:400]!r}, value={value[:400]!r}, '
                   f'stdout={result.stdout[:1000]!r}, stderr={result.stderr[:1000]!r}')
        if source_file.read_bytes() != source:
            raise AssertionError(f'editor modified input file: {context}')
        if value_file.read_bytes() != value:
            raise AssertionError(f'editor modified replacement file: {context}')
        if any(marker in result.stderr for marker in
               (b'AddressSanitizer', b'UndefinedBehaviorSanitizer', b'runtime error:', b'LeakSanitizer')):
            raise AssertionError(f'sanitizer diagnostic: {context}')
        if rejected:
            # A crash or sanitizer abort is not an acceptable rejection.
            if result.returncode != 1 or output_file.exists():
                raise AssertionError(f'expected clean rejection without output: {context}')
            return None
        if result.returncode != 0 or not output_file.is_file():
            raise AssertionError(f'expected success and owned output: {context}')
        output = output_file.read_bytes()
        if len(output) > LIMIT:
            raise AssertionError(f'oversized successful result: {context}')
        if expected is not None and output != expected:
            raise AssertionError(f'byte preservation failure: {context}, output={output[:1000]!r}')
        # This independent parse catches a successful edit producing invalid TOML.
        try:
            parse(output)
        except (UnicodeError, tomllib.TOMLDecodeError) as error:
            raise AssertionError(f'invalid successful result: {context}') from error
        return output

    def semantic(self, mode, source, path, value=b''):
        before = parse(source)
        expected = copy.deepcopy(before)
        if mode == 'set':
            replacement = parse(b'value = ' + value)['value']
            parent(expected, path, create=True)[path[-1]] = replacement
        else:
            parent(expected, path).pop(path[-1], None)
        output = self.call(mode, source, path, value)
        actual = parse(output)
        if not same(actual, expected):
            raise AssertionError(f'semantic mismatch for {mode} {path!r}: '
                                 f'expected={expected!r}, actual={actual!r}, '
                                 f'source={source!r}, output={output!r}')
        return output


VALUES = [
    b'0', b'-9223372036854775808', b'9223372036854775807', b'0x7fff',
    b'1_234_567', b'-0.25', b'-0.0', b'1.25e+4', b'true', b'false',
    b'"plain"', b"'literal # [not.a.header]'", '"é🪿"'.encode(),
    b'"escaped\\nline\\tend"', b'"""first\n[not.a.header]\n# still string\nlast"""',
    b"'''raw\nkey = 42\n# string, not comment'''",
    b'[]', b'[1, true, "three"]', b'[\n 1, # preserved within new value\n 2,\n]',
    b'{ path = "../lib", enabled = true, versions = [1, 2] }',
    b'1979-05-27', b'07:32:00', b'1979-05-27T07:32:00Z',
    b'1979-05-27 07:32:00.123456789+07:00',
]


def fixed(campaign):
    source = b'# leading\n[dependencies] # section\n  goose = { path = "../old" }  # keep me\n\n[package]\nname = "app"\n'
    campaign.call('set', source, ['dependencies', 'goose'], b'{ path = "../new" }',
                  expected=source.replace(b'{ path = "../old" }', b'{ path = "../new" }'))
    campaign.call('remove', source, ['dependencies', 'goose'],
                  expected=source.replace(b'goose = { path = "../old" }', b''))
    campaign.call('remove', source, ['dependencies', 'absent'], expected=source)
    for newline in (b'\n', b'\r\n'):
        for terminal in (b'', newline):
            original = newline.join([b'# top', b'[section] # header', b'x\t=\t"old" # trailing']) + terminal
            campaign.call('set', original, ['section', 'x'], b"'''new\n[looks.like.header]\n# string'''",
                          expected=original.replace(b'"old"', b"'''new\n[looks.like.header]\n# string'''"))
            inserted = campaign.semantic('set', original, ['section', 'added'], b'42')
            if original.endswith(b'\r\n') and b'\n' in inserted.replace(b'\r\n', b''):
                raise AssertionError('CRLF insertion introduced a bare LF')
    # A header with no newline at EOF is an insertion anchor, not value syntax.
    campaign.semantic('set', b'# intro\r\n[dependencies] # no final newline',
                      ['dependencies', 'foo'], b'{ path = "../foo" }')
    campaign.semantic('set', b'key = 1 # root without newline', ['added'], b'true')
    campaign.semantic('set', b'[dependencies.foo]\npath = "../foo"\n[dependencies]\nbar = { path = "../bar" }\n',
                      ['dependencies', 'new'], b'{ path = "../new" }')
    # Delete scattered descendants, preserving unrelated sections and comments.
    original = (b'# untouched\n[dependencies.foo] # dependency note\npath = "../foo" # path note\n'
                b'[other]\nvalue = [1, 2]\n[dependencies.foo.options]\nenabled = true\n'
                b'[dependencies.bar]\npath = "../bar"\n')
    expected = (b'# untouched\n # dependency note\n # path note\n'
                b'[other]\nvalue = [1, 2]\n\n\n'
                b'[dependencies.bar]\npath = "../bar"\n')
    campaign.call('remove', original, ['dependencies', 'foo'], expected=expected)
    campaign.semantic('remove', original, ['dependencies', 'foo'])
    original = b'a.b = 1 # first\na.c = 2 # second\nkeep = "same"\n'
    campaign.call('remove', original, ['a'],
                  expected=b' # first\n # second\nkeep = "same"\n')
    # Quoted dots, empty names and escaped keys are genuine decoded components.
    for component in ('', 'literal.dot', 'two words', 'quote"key', 'é🪿', 'tab\tkey', 'line\nkey'):
        campaign.semantic('set', b'keep = "same"\n', [component], b'42')
        original = (key(component) + ' = 1 # exact suffix\nkeep = "same"\n').encode()
        campaign.semantic('set', original, [component], b'2')
        campaign.semantic('remove', original, [component])
    campaign.semantic('set', b'dep = { path = "../old" }\n', ['dep'], b'{ path = "../new" }')
    # Arrays of tables away from the selected path must remain byte-identical.
    original = b'root = 1\n[[unrelated]]\nx = 2\n[[unrelated]]\nx = 3\n'
    campaign.call('set', original, ['root'], b'4', expected=original.replace(b'root = 1', b'root = 4'))


def adversarial(campaign):
    source = b'x = 1 # attached comment must remain\nkeep = "same"\n'
    bad_values = [b'', b' ', b'2 # swallow original', b'2\nx = 3', b'2\n',
                  b'2\r\n', b'2\n[another]\ninjected = true', b'"unterminated',
                  b'{ a = 1, a = 2 }', b'9223372036854775808', b'"\xff"',
                  b'[[[[', b'[' * 65 + b'0' + b']' * 65, b'1' * (LIMIT + 1)]
    for value in bad_values:
        campaign.call('set', source, ['x'], value, rejected=True)
        campaign.call('set', source, ['new'], value, rejected=True)
    # Horizontal whitespace surrounding one value is permitted.
    campaign.semantic('set', source, ['x'], b' \t 2 \t')
    bad_sources = [b'\xff', b'# \xff\nx = 1\n', b'x = "\xff"\n', b'x = 1\rx = 2',
                   b'x = 1\nx = 2\n', b'x = "unterminated', b'[a]\n[a]\n',
                   b'x = [1,', b'x = 1\ntrailing garbage', b'#' + b'x' * LIMIT]
    for original in bad_sources:
        for mode in ('set', 'remove'):
            campaign.call(mode, original, ['x'], b'2', rejected=True)
    for original, path in [
        (b'a = { b = 1 }\n', ['a', 'b']),
        (b'a = { b = 1 }\n', ['a', 'new']),
        (b'a = [1, 2]\n', ['a', 'x']),
        (b'a = 1\n', ['a', 'x']),
        (b'[[a]]\nb = 1\n[[a]]\nb = 2\n', ['a', 'b']),
    ]:
        for mode in ('set', 'remove'):
            campaign.call(mode, original, path, b'2', rejected=True)
    campaign.call('set', b'[a]\nx = 1\n', ['a'], b'2', rejected=True)
    # Full output/input limits, including comments, not only semantic values.
    exact = b'#' + b'x' * (LIMIT - 2) + b'\n'
    campaign.call('remove', exact, ['missing'], expected=exact)
    campaign.call('set', exact, ['x'], b'1', rejected=True)
    for mode in ('set', 'remove'):
        campaign.call(mode, exact + b'\n', ['x'], b'2', rejected=True)
        campaign.call(mode, b'x = 1\n', ['key'] * 65, b'2', rejected=True)
    # The combined path/value depth can exceed the limit although each passes
    # its own preflight. A successful result must still parse under both parsers.
    campaign.call('set', b'', ['key'] * 64, b'[0]', rejected=True)


def generated(campaign, cases, seed):
    rng = random.Random(seed)
    names = ['simple', 'literal.dot', 'spaced name', '', 'quote"key', 'é🪿', 'bracket]key']
    for sample in range(cases):
        newline = rng.choice(['\n', '\r\n'])
        layout = rng.randrange(4)
        table = [] if layout == 0 else [rng.choice(names) + str(sample)]
        if layout == 3:
            table.append('nested.' + str(sample))
        keys = [rng.choice(names) + '_' + str(index) for index in range(5)]
        values = [rng.choice(VALUES) for _ in keys]
        lines = ['# stable leading comment ' + str(sample)]
        if layout in (1, 3):
            lines += ['[' + dotted(table) + '] # stable section comment']
        for index, (name, value) in enumerate(zip(keys, values)):
            path = table + [name] if layout == 2 else [name]
            spelling = dotted(path)
            spacing = rng.choice([' = ', '\t=\t', '  = '])
            lines.append(' ' * rng.randrange(3) + spelling + spacing + value.decode() +
                         ' # stable trailing ' + str(index))
        lines += ['', '[unrelated]', 'unchanged = "sentinel-' + str(sample) + '" # keep']
        source = newline.join(lines).encode() + rng.choice([b'', newline.encode()])
        # All generated fixtures independently parse before invoking the editor.
        parse(source)
        operation = sample % 4
        if operation == 0:
            campaign.semantic('set', source, table + [rng.choice(keys)], rng.choice(VALUES))
        elif operation == 1:
            campaign.semantic('set', source, table + ['new.' + str(sample)], rng.choice(VALUES))
        elif operation == 2:
            campaign.semantic('remove', source, table + [rng.choice(keys)])
        else:
            campaign.call('remove', source, table + ['absent'], expected=source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=360)
    parser.add_argument('--seed', type=int, default=SEED)
    args = parser.parse_args()
    if not 1 <= args.cases <= 100_000:
        parser.error('--cases must be between 1 and 100000')
    with tempfile.TemporaryDirectory(prefix='goose-toml-edit-property-') as temp:
        campaign = Campaign(args.runner.resolve(), Path(temp))
        fixed(campaign)
        adversarial(campaign)
        generated(campaign, args.cases, args.seed)
        print(f'Passed {campaign.calls} public editor calls; '
              f'{args.cases} generated cases, seed {args.seed}; Python tomllib oracle')


if __name__ == '__main__':
    main()
