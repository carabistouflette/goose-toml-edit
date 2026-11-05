# Validation

The editor and engine in main match released v0.1.1: the companion uses canonical
TOML `fe849141405009e36e1cce6eb479b395eae18f1a` (alpha.3). Later main changes add
release-verifier tooling and documentation. [The release receipt](results/release-v0.1.1.md)
records publication, the original isolated Honk acceptance and later combined
Honk adoption. These are distinct checks.

## Run checks

After `make setup` installs the compiler pinned in `GOOSE_REVISION`:

```sh
make check test property
make sanitize SANITIZER_CC=gcc
make sanitize SANITIZER_CC=clang
```

Use `GOOSE=/absolute/path/to/goose` to reuse the exact pinned compiler. The current
hosted [CI workflow](https://github.com/carabistouflette/goose-toml-edit/actions/workflows/ci.yml)
runs these targets; its benchmark step checks execution, not timing thresholds.

Direct Goose suites cover input/output aliasing, error ownership and clearing,
malformed UTF-8/TOML, strict fragment suffixes, decoded keys, unsupported paths,
exact/overflow input and parser bounds, combined result limits, and consumer
`str`/`copy` and conversion overloads. They run interpreted, optimized and
debug/no-bounds-check-elimination variants. GCC/Clang ASan/UBSan builds instrument
generated C and the Goose runtime, with leak detection enabled.

The property runner uses Python `tomllib` for a shared TOML 1.0 subset and exact
byte expectations for preservation. The frozen 21-case
[legacy fixture](../tests/fixtures/README.md) is hash-checked before use. Optional
legacy comparisons require a separately preserved reference binary and compare
status, output and diagnostic bytes, never candidate-generated expectations.
The parser and Python have different resource/scalar limits; finite generated
cases do not prove complete TOML equivalence or absence of defects.

Python tests check vendor hashes and release-verifier archive/identity failures,
including optimized Python. Main also tests shared network deadlines with
loopback/DNS fixtures and owned worker cleanup. These correctness deadlines are
not editor performance measurements.

## Cost and evidence

Each call parses the source and validates the complete output; set also parses
its replacement value. Canonical result parsing reuses parser storage only after
original edit metadata is consumed. Lookup walks siblings, removal tracks
selected nodes, and insertion indexes header contexts. Storage includes bounded
parser arenas, statement/index buffers, selections and owned text. No per-call
allocation count or universal speedup is claimed.

The [measurement guide](../bench/README.md) distinguishes current-engine evidence
from older implementations, retains slower results and links raw samples,
reproducers and source hashes. The [announcement audit](announcement-readiness.md)
records the checked runtime/compiler/harness bridge and example validation.

Historical records remain unchanged: [original adapter](results/adapter-de7dfe0-validation.json),
[successor candidate](results/adapter-fe849-validation.json),
[canonical final parity](results/canonical-04c8bef-parity.json), and
[earlier parity](results/canonical-5cca023-parity.json). Their pending statements
and implementation descriptions refer to those stages. Completed acceptance and
publication are recorded in the separate release receipt, not retroactively
inserted into the historical snapshots.
