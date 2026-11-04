#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Paired complete public-call measurements against a preserved legacy export."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(root):
    manifest = json.loads((root / 'vendor/manifest.json').read_text())
    paths = ['toml_edit.goose', 'bench/edit.goose', 'GOOSE_REVISION', 'vendor/manifest.json']
    paths += ['vendor/' + library['directory'] + '/' + name
              for library in manifest['libraries'] for name in library['files']]
    return {name: digest(root / name) for name in paths}


def call(command):
    return subprocess.check_output(command, text=True, timeout=120).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--baseline-source', type=Path, required=True)
    parser.add_argument('--baseline-revision', required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--goose', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=9)
    parser.add_argument('--iterations', type=int, default=30)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 100 or not 1 <= args.iterations <= 10000:
        parser.error('invalid round/iteration count')
    root = Path(__file__).resolve().parents[1]
    baseline_root = args.baseline_source.resolve()
    sources = {'baseline': fingerprint(baseline_root), 'candidate': fingerprint(root)}
    # Establish baseline identity against immutable Git objects, not a label.
    for name, expected in sources['baseline'].items():
        blob = subprocess.check_output(['git', 'show', args.baseline_revision + ':' + name], cwd=root)
        if hashlib.sha256(blob).hexdigest() != expected:
            raise AssertionError(f'baseline export differs: {name}')
    runners = {'baseline': args.baseline.resolve(), 'candidate': args.candidate.resolve()}
    hashes = {name: digest(path) for name, path in runners.items()}
    cpu = min(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu})
    cases = ['set', 'insert', 'remove', 'wide', 'deep', 'comments']
    checksums = {}
    for case in cases:
        values = [tuple(map(int, call([str(path), case, '1']).split())) for path in runners.values()]
        if any(elapsed <= 0 for elapsed, _ in values) or values[0][1] != values[1][1]:
            raise AssertionError(f'preflight mismatch: {case}, {values}')
        checksums[case] = values[0][1]
    seed = 20261104
    rng = random.Random(seed)
    samples = []
    for round_index in range(args.rounds):
        order = cases.copy(); rng.shuffle(order)
        for case_index, case in enumerate(order):
            names = ['baseline', 'candidate']
            if (round_index + case_index) % 2:
                names.reverse()
            for name in names:
                elapsed, checksum = map(int, call([str(runners[name]), case, str(args.iterations)]).split())
                if elapsed <= 0 or checksum != checksums[case] * args.iterations:
                    raise AssertionError(f'measurement mismatch: {name}, {case}')
                samples.append({'round': round_index, 'case': case, 'runner': name,
                                'elapsed_ns': elapsed, 'checksum': checksum})
    if sources != {'baseline': fingerprint(baseline_root), 'candidate': fingerprint(root)} or hashes != {
            name: digest(path) for name, path in runners.items()}:
        raise AssertionError('source or binary changed during measurements')
    medians = {name: {case: statistics.median(sample['elapsed_ns'] / args.iterations
                 for sample in samples if sample['runner'] == name and sample['case'] == case)
                 for case in cases} for name in runners}
    report = {'baseline_revision': args.baseline_revision,
              'candidate_revision': call(['git', '-C', str(root), 'rev-parse', 'HEAD']),
              'candidate_dirty': bool(call(['git', '-C', str(root), 'status', '--porcelain'])),
              'compiler_revision': (root / 'GOOSE_REVISION').read_text().strip(),
              'compiler_sha256': digest(args.goose.resolve()),
              'toolchain': json.loads(call([str(args.goose.resolve()), 'toolchain', '--json'])),
              'build': 'goose build bench/edit.goose -O2; same compiler/toolchain for both runners',
              'platform': platform.platform(), 'cpu_affinity': cpu,
              'cpu_model': next(line.split(':', 1)[1].strip() for line in
                  Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),
              'rounds': args.rounds, 'iterations': args.iterations, 'seed': seed,
              'limitations': 'Shared host, no exclusive CPU claim. Fixture construction/process startup '
                  'excluded by runner clock; parsing, validation, allocation and output copying included. '
                  'Alternating paired order and shuffled cases reduce order bias; finite workload evidence only.',
              'source_sha256': sources, 'binary_sha256': hashes,
              'reproducer_sha256': digest(Path(__file__)), 'checksums_per_call': checksums,
              'samples': samples, 'medians_ns_per_call': medians}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f'Retained {len(samples)} checked samples in {args.output}')


if __name__ == '__main__':
    main()
