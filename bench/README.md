# Public-call measurements

Measurements include complete `set`/`remove` calls: parsing, selection, copying,
result validation and owned output replacement. Process startup and fixture
construction are outside the runner clock. They exclude file I/O and atomic
saving, and do not measure another library or worst-case latency.

## Which implementation is measured?

The latest relevant retained experiment used released companion `ae32f13` with
only its canonical editor replaced by checkpoint `a79cf60`. The measured editor
hash is `1fa20fcb1bb3c7ad1751788ae34d6c91dd348397e8871283da6c687c222b59c1`.
All 12 recorded runtime/vendor/compiler-pin/harness inputs match released
v0.1.1 (`f8d1b166`) and audited main (`7ae73b9b`) exactly; the
[source bridge](../docs/benchmark-source-bridge.json) records each hash.

The old experiment deliberately retained ae32's old vendor manifest. That
manifest mismatch was an isolated measurement setup, not a valid released
snapshot. Current v0.1.1 has the separately checked manifest pinning `fe849141`.
The upstream report's pre-promotion hold is historical; the
[release receipt](../docs/results/release-v0.1.1.md) records later approval and
publication. These distinctions support reusing the compiled-code measurements
without presenting them as a new run of the released archive.

## Protocol and environment

Linux 7.2.11-arch1-1 x86-64, glibc 2.44, Intel Core Ultra 7 258V, CPU6.
Both runners used the same Goose `eadca409f68210893f366e60d0c2f0dc29a339be`
executable (SHA-256 `3cad45a18356bf97f4732f1da2012252afd77a652932ddb9c91c5551c04904be`),
GCC 16.2.1 (20260810), `--cc gcc -O2`. The library has no native runtime
packages; the vendored parser/text identities are in the source bridge.

Each series has nine shuffled rounds, alternating per-case runner order,
six workloads and two labels: 108 aggregate samples. Calibration targeted 30 ms
per aggregate, with a 10 ms eligibility minimum. Counts are: set/insert
2 × 10,000 calls, remove 4 × 10,000, wide/comments 8 calls, deep 4,000 calls.
Every recorded aggregate in the first, confirmation and control meets the
minimum. Each component process starts fresh: its first library use is included
and amortized; there are no extra untimed warmups within that process.
Calibration exercised calls separately. All component durations/checksums remain
in the raw reports.

The host was shared; earlier work on other CPUs overlapped some initial series.
CPU affinity does not provide isolation or fixed frequency. The unchanged-binary
control runs the same baseline under both labels and exposes run variation; it
is not a confidence interval or an uncertainty bound.

## Confirmation results

Candidate batch-average medians and full min–max ranges, **µs per public call**:

| Case | Median µs/call | Sample range µs/call |
| --- | ---: | ---: |
| set | 1.357 | 1.273–1.510 |
| insert | 1.645 | 1.435–2.165 |
| remove | 1.024 | 0.936–1.148 |
| wide | 4778.682 | 4280.422–5196.893 |
| deep | 8.099 | 7.589–12.938 |
| comments | 3595.820 | 3330.177–4531.383 |

The tiny cases use a package/dependency document; wide replaces `key5000` among
10,000 assignments; deep inserts through 63 table ancestors; comments replaces
a scalar beside a 1,000,000-byte comment. The exact fixture is
[bench/edit.goose](edit.goose); all six cases remain reported.

Changes below are candidate/baseline ratios of medians minus one. Positive
means slower. Every result, including regressions, is retained:

| Case | First | Confirmation | Unchanged control |
| --- | ---: | ---: | ---: |
| set | +2.6% | +1.5% | +0.5% |
| insert | +0.3% | +2.7% | +2.8% |
| remove | -1.0% | +1.3% | +4.3% |
| wide | -7.7% | -7.1% | -1.8% |
| deep | -3.1% | -4.7% | +0.8% |
| comments | -3.0% | -0.2% | +3.9% |

The wide case repeats a reduction larger than its unchanged control. Tiny and
comment-heavy changes are mixed or close to host/run variation. This is not a
universal speedup or per-call allocation claim. The older de7 adapter comparison
also retained a comment-heavy slowdown; it remains historical evidence below.

Raw samples, all input/binary identities and embedded producer source:
- [First](https://github.com/carabistouflette/goose-toml/blob/fe849141405009e36e1cce6eb479b395eae18f1a/source/tests/results/document-reuse/public-batched-paired.json)
- [Confirmation](https://github.com/carabistouflette/goose-toml/blob/fe849141405009e36e1cce6eb479b395eae18f1a/source/tests/results/document-reuse/public-batched-repeat.json)
- [Unchanged control](https://github.com/carabistouflette/goose-toml/blob/fe849141405009e36e1cce6eb479b395eae18f1a/source/tests/results/document-reuse/public-batched-control.json)

## Reproduce

After setup, a basic smoke/sample run is:

```sh
make bench BENCH_ITERATIONS=30
```

This uses seven rounds and one untimed process call per case; 30-call tiny
batches can be too short for useful timing claims. It is not the aggregated
historical protocol above. Request a finite measurement window before timing on
a shared host.

For a fresh comparison against v0.1.0, export the exact baseline and use the
current paired driver (it rebuilds both binaries with one compiler):

```sh
mkdir -p .build/baseline-ae32
git archive ae32f13d69b69c9604a44d7acd71d2f966daef35 | tar -x -C .build/baseline-ae32
python3 bench/compare.py --baseline .build/bench-baseline \
  --baseline-source .build/baseline-ae32 \
  --baseline-revision ae32f13d69b69c9604a44d7acd71d2f966daef35 \
  --candidate .build/bench-candidate --goose .toolchain/goose/build/goose \
  --rounds 9 --iterations 30 --small-iterations 1000 \
  --output .build/comparison.json
```

This fresh command uses the driver's per-process protocol, not the historical
aggregate protocol. To reproduce the latter, use the producer source embedded
in its public JSON: export ae32 twice, replace only one export's editor with the
exact fe849 file, build both using the recorded compiler/flags, then calibrate
and run the fixed aggregate counts above. Retain the intentional manifest
mismatch, complete before/after fingerprints, first/confirmation/control samples
and any changed local paths/build identities as new provenance. The original
workstation paths are normalized in the public artifact; their byte hashes and
normalization note remain recorded separately. Do not adopt that overlay.

## Older implementations

[Initial editor measurements](results/2026-11-04/README.md) and the
[de7 canonical-adapter comparison](results/canonical-adapter/README.md) retain
all earlier raw samples, including both short/long-loop series and slower
results. They do not measure the current terminal-Document-reuse engine. No raw
artifact or image was replaced, and no new timing campaign was run in this audit.
