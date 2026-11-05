# Initial full-call benchmark

Historical implementation and measurements. See the [current measurement guide](../../README.md) for the released alpha.3 engine, checked source bridge and sample dispersion.

[Raw samples and provenance](inspection.json) describe seven randomized rounds
of30 warmed calls per workload, seed20261104, CPU0, on a shared Linux x86-64 host.
The source SHA identifies the editor/tests and harness; the dirty flag reflects
in-progress CI/Makefile changes. The editor and harness hashes identify measured
code exactly. No exclusive-core or fixed-frequency claim is made.

Workloads are tiny Honk-style assignment replacement/insertion/removal, replacing
one key in10,000 assignments, insertion through63 table ancestors, and replacing
a scalar next to a1,000,000-byte comment. Fixture construction is outside timing.
Each call includes parsing, selection, splice construction, complete output
validation and owned output replacement. Output length and boundary-byte
checksums are verified. Read/write I/O is not measured. Run:

```sh
make bench GOOSE=/absolute/path/to/pinned/goose
```

The runner preserves every raw sample, median, checksum, compiler identity/hash,
selected toolchain, platform/CPU, source/harness/editor/binary hashes and build
flags. Measurements establish an initial baseline; there is no competing editor
comparison, before/after optimization claim, allocation count or timing threshold.
