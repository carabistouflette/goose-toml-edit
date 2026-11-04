#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Warmed complete public calls, including validation and owned output replacement."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--goose',type=Path,required=True)
p.add_argument('--runner',type=Path,required=True)
p.add_argument('--iterations',type=int,default=30)
p.add_argument('--runs',type=int,default=7)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
if not 1<=a.iterations<=10000 or not 1<=a.runs<=100: p.error('invalid run count')
def call(*args): return subprocess.check_output(args,text=True,timeout=120).strip()
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
cases=['set','insert','remove','wide','deep','comments'];samples={k:[] for k in cases};checksums={}
runner=str(a.runner.resolve())
for case in cases:
    _,checksum=map(int,call(runner,case,'1').split());checksums[case]=checksum
rng=random.Random(20261104)
for _ in range(a.runs):
    rng.shuffle(cases)
    for case in cases:
        elapsed,checksum=map(int,call(runner,case,str(a.iterations)).split())
        assert elapsed>0 and checksum==checksums[case]*a.iterations
        samples[case].append(elapsed/a.iterations)
report={'source':call('git','rev-parse','HEAD'),'source_dirty':bool(call('git','status','--porcelain')),
    'compiler_revision':Path('GOOSE_REVISION').read_text().strip(),'goose_version':call(str(a.goose.resolve()),'version'),
    'goose_sha256':digest(a.goose.resolve()),'binary_sha256':digest(a.runner.resolve()),
    'harness_sha256':digest(Path('bench/edit.goose')),'editor_sha256':digest(Path('toml_edit.goose')),
    'toolchain':json.loads(call(str(a.goose.resolve()),'toolchain','--json')),
    'platform':platform.platform(),'machine':platform.machine(),'cpu_affinity':cpu,
    'cpu_model':next(x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name')),
    'build':'goose build bench/edit.goose -O2 (generated C, selected toolchain)',
    'iterations':a.iterations,'runs':a.runs,'seed':20261104,'units':'ns per public call',
    'samples':samples,'medians':{k:statistics.median(v) for k,v in samples.items()},'checksums_per_call':checksums}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report['medians'],indent=2))
