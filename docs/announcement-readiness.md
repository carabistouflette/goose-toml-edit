# Documentation audit: TOML editor

Task: `GL-DOCSTOMLEDIT-01`. Audited public main:
`7ae73b9b6463ffff96b596687d7637047d81c5cb`. Latest release: experimental
v0.1.1 at `f8d1b1664a86b768a6f1375636d9b2c3a440aa31`. The editor, vendored
engine, compiler pin and benchmark fixture are identical between those revisions.
Main adds release-verifier deadlines/tests and documentation; it does not adopt
a newer canonical engine than the recorded `fe849141` pin.

## Coverage and changes

Reviewed all tracked Markdown: README, contributing/security/third-party guides,
validation/release-verification guides, release receipt, both historical benchmark
READMEs, test-fixture instructions and the two pinned upstream README snapshots.
Also checked the maintained dependency example, CLI/reproduction recipes and
benchmark producers. Historical JSON, image and frozen fixture artifacts remain
unchanged. Pinned upstream prose remains byte-identical: its relative paths refer
to the original [canonical repository at fe849](https://github.com/carabistouflette/goose-toml/tree/fe849141405009e36e1cce6eb479b395eae18f1a),
not a complete upstream checkout inside this companion. It describes both source
profiles and older results; the companion's [API guide](api.md) defines its own
supported contract.

README now has purpose, a short runnable quickstart, API/limits and release/main
scope. The API guide retains import mappings, exact preservation, errors and
precedence, aliases, unsupported layouts and conservative insertion bounds.
Validation links historical evidence separately. Release-verifier docs explain
that the network-deadline option exists on main but not in the v0.1.1 tag.
Security reporting links the enabled private GitHub channel. Third-party notices
name the actually retained TOML/text sources and licenses.

## Commands and examples

After the coordinator released the local-check hold, a single bounded check set
used a fresh anonymous HTTPS clone at audited public main and a clean compiler
at `eadca409f68210893f366e60d0c2f0dc29a339be`. Its executable SHA-256 was
`3cad45a18356bf97f4732f1da2012252afd77a652932ddb9c91c5551c04904be`.

- The README's `goose run examples/dependency.goose` command passed.
- The full API example ran with sibling local root imports.
- The same example ran with exact remote imports of released companion `f8d1`
  and canonical `fe849`. Both dependencies were fetched successfully.
- `make check` passed: 28 Python methods, vendor hashes, Goose formatting and all
  documented type-check roots. `git diff --check` and relative links passed.

All three applications printed the preserved `# keep` comment, dependency header
and inserted `"text"` assignment. Setup recipes were inspected; the compiler was
reused at its exact pin rather than bootstrapped again. No new sanitizer/fuzz or
timing campaign was needed for documentation. Existing hosted CI still runs the
normal correctness/property/sanitizer suites and benchmark execution smoke.

## Performance currentness

The [source bridge](benchmark-source-bridge.json) checks 12 runtime/vendor,
compiler-pin and benchmark-harness files against the published experiment,
released v0.1.1 and audited main. The measured engine is exactly the current
pinned engine; the old experiment's intentionally mismatched manifest is not
represented as a valid released snapshot. Current manifest bytes and pin are
checked separately. The compiler executable used for example checks matches
the measured compiler hash.

The [measurement guide](../bench/README.md) includes machine/OS/compiler/build
scope, calibrated counts, repeats, controls, raw links, every candidate median
and full sample range, and all signed first/confirmation/control changes. Earlier
legacy/de7 results and regressions remain explicitly historical. The published
producer source and before/after fingerprints remain linked for reproduction;
normalized public artifacts distinguish their hashes from original local bytes.
No timing rerun is necessary for unchanged compiled inputs and fixture code.
No universal speedup, per-call allocation saving or file-I/O claim is made.

Release-verifier throughput benchmarks are N/A: this administrative tool makes
no performance claim. Its network budget and cleanup behavior have correctness
regressions, not editor throughput measurements.

## Remaining limits

Experimental API; TOML 1.0 only; no array indexing or inline-table child edits,
header-table replacement, formatting cleanup or batch edits. Input/path/result
and parser caps remain; insertion can conservatively reject a key that would
fit. Applications own bounded I/O, repeated calls and atomic saving. Current CI
is Linux; no untested platform support or strict RSS/wall-clock bound is claimed.
Measured movement on a shared host is workload-specific; all finite tests and
checks leave possible defects. Existing tags and dependency pins are unchanged.
