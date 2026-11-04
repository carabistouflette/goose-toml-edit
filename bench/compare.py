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
    parser.add_argument('--baseline', type=Path, required=True, help='output path for fresh baseline binary')
    parser.add_argument('--baseline-source', type=Path, required=True)
    parser.add_argument('--baseline-revision', required=True)
    parser.add_argument('--candidate', type=Path, required=True, help='output path for fresh candidate binary')
    parser.add_argument('--goose', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=9)
    parser.add_argument('--iterations', type=int, default=30)
    parser.add_argument('--small-iterations', type=int, default=1000,
                        help='longer loops for set/insert/remove/deep to amortize first-call effects')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 100 or not all(1 <= count <= 10000 for count in
                                           (args.iterations, args.small_iterations)):
        parser.error('invalid round/iteration count')
    root = Path(__file__).resolve().parents[1]
    reproducer_hash = digest(Path(__file__))
    baseline_revision = call(['git', '-C', str(root), 'rev-parse', '--verify',
                              '--end-of-options', args.baseline_revision + '^{commit}'])
    baseline_root = args.baseline_source.resolve()
    sources = {'baseline': fingerprint(baseline_root), 'candidate': fingerprint(root)}
    for name in ('bench/edit.goose', 'GOOSE_REVISION'):
        if sources['baseline'][name] != sources['candidate'][name]:
            raise AssertionError(f'comparison requires identical {name}')
    # Establish baseline identity against immutable Git objects, not a label.
    for name, expected in sources['baseline'].items():
        blob = subprocess.check_output(['git', 'show', baseline_revision + ':' + name], cwd=root)
        if hashlib.sha256(blob).hexdigest() != expected:
            raise AssertionError(f'baseline export differs: {name}')
    runners = {'baseline': args.baseline.resolve(), 'candidate': args.candidate.resolve()}
    if runners['baseline'] == runners['candidate']:
        parser.error('baseline and candidate output paths must differ')
    compiler_hash = digest(args.goose.resolve())
    builds = {}
    for name, directory in (('baseline', baseline_root), ('candidate', root)):
        runners[name].parent.mkdir(parents=True, exist_ok=True)
        command = [str(args.goose.resolve()), 'build', 'bench/edit.goose', '--cc', 'cc',
                   '-O2', '-o', str(runners[name])]
        subprocess.run(command, cwd=directory, check=True, timeout=120, capture_output=True)
        builds[name] = {'command': command, 'source_sha256': sources[name],
                        'compiler_sha256': compiler_hash, 'binary_sha256': digest(runners[name])}
    hashes = {name: digest(path) for name, path in runners.items()}
    cpu = min(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu})
    cases = ['set', 'insert', 'remove', 'wide', 'deep', 'comments']
    iterations = {case: args.iterations if case in ('wide', 'comments') else args.small_iterations
                  for case in cases}
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
                count = iterations[case]
                elapsed, checksum = map(int, call([str(runners[name]), case, str(count)]).split())
                if elapsed <= 0 or checksum != checksums[case] * count:
                    raise AssertionError(f'measurement mismatch: {name}, {case}')
                samples.append({'round': round_index, 'case': case, 'runner': name,
                                'iterations': count, 'elapsed_ns': elapsed, 'checksum': checksum})
    if reproducer_hash != digest(Path(__file__)) or compiler_hash != digest(args.goose.resolve()) or sources != {
            'baseline': fingerprint(baseline_root), 'candidate': fingerprint(root)} or hashes != {
            name: digest(path) for name, path in runners.items()}:
        raise AssertionError('source or binary changed during measurements')
    medians = {name: {case: statistics.median(sample['elapsed_ns'] / sample['iterations']
                 for sample in samples if sample['runner'] == name and sample['case'] == case)
                 for case in cases} for name in runners}
    report = {'baseline_revision': baseline_revision,
              'candidate_revision': call(['git', '-C', str(root), 'rev-parse', 'HEAD']),
              'candidate_dirty': bool(call(['git', '-C', str(root), 'status', '--porcelain'])),
              'compiler_revision': (root / 'GOOSE_REVISION').read_text().strip(),
              'compiler_sha256': compiler_hash,
              'toolchain': json.loads(call([str(args.goose.resolve()), 'toolchain', '--json'])),
              'build': 'Both runners freshly built by this script with goose build --cc cc -O2',
              'builds': builds, 'cc_version': call(['cc', '--version']),
              'platform': platform.platform(), 'cpu_affinity': cpu,
              'cpu_model': next(line.split(':', 1)[1].strip() for line in
                  Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),
              'rounds': args.rounds, 'iterations_per_case': iterations, 'seed': seed,
              'limitations': 'Shared host, no exclusive CPU claim. Fixture construction/process startup '
                  'excluded by runner clock; parsing, validation, allocation and output copying included. '
                  'Alternating paired order and shuffled cases reduce order bias; finite workload evidence only.',
              'source_sha256': sources, 'binary_sha256': hashes,
              'reproducer_sha256': reproducer_hash, 'checksums_per_call': checksums,
              'samples': samples, 'medians_ns_per_call': medians}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f'Retained {len(samples)} checked samples in {args.output}')


if __name__ == '__main__':
    main()
