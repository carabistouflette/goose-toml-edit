# Validation and limits

Validated with the exact upstream Goose compiler in GOOSE_REVISION. The vendor
manifest records an unmodified goose-toml snapshot and its nested sources and
licenses. `scripts/check-vendor.py` checks every recorded source/license hash.

Public tests run in interpreted, optimized compiled and debug/no-BCE modes.
Boundary tests cover control-character and Unicode keys, owned outputs, aliasing
source/output, clearing output after errors, exact/overflow input bytes, combined
value depth and the exact/overflow 65,536-node limit. Missing-key edits compare
the instrumented scanner's acceptance and output against the original parser.

The independent `scripts/property-test.py` campaign uses Python `tomllib` for
semantic checking and exact expected bytes for untouched regions. The extended
local run passed 5,107 public calls (5,000 generated cases, seed20261104), covering
LF/CRLF, EOF without newline, quoted/dotted keys, comments, multiline values,
insertion/replacement/removal, interleaved subtree declarations, injection
suffixes, malformed UTF-8/TOML, unsupported containers and size/depth failures.
Python and the Goose parser have different scalar/resource limits; generated
semantic cases stay inside their common supported domain.

Both GCC and Clang ASan/UBSan builds instrument the generated C and Goose runtime,
with leak detection enabled. They run the boundary/smoke suites and 207 property
calls per toolchain (100 generated cases plus fixed regressions). Clang emits an
alignment warning in generated standard-library frexp glue; the executed
sanitizers report no runtime issue. No compiler changes are included.

Repeated independent correctness/security and quality/performance reviews found
one key-encoding bug: JSON escaping did not escape DEL. The fix delegates to the
pinned TOML encoder, with control-key round trips. Follow-up reviews found no
remaining blocker. Independent review probes additionally passed 133 key/scope
calls, 3,032 parser/scanner prefix/byte-mutation parity cases, and 607 property
calls using seed271828. These finite checks do not establish absence of defects.

The first Honk integration keeps the source snapshot and semantic validation
under its existing project lock, performs output semantic validation, then uses
the existing atomic save. Five byte-exact CLI groups cover formatting/comment
preservation, dependency layouts, new sections/dev dependencies/EOF and unchanged
originals on unsupported/invalid/oversized edits. Full Honk checks/tests and its
sanitizer suite passed in an isolated checkout.

## Resource and cost model

Each call borrows its inputs and returns owned text only after complete success.
Input, intermediate output and final output are bounded at1MiB. Paths have at
most64 decoded components and1MiB combined decoded bytes. Key rendering reserves
six encoded bytes per decoded byte plus quotes/separators, so large ordinary keys
can be conservatively rejected. The underlying parser enforces node/depth and
key-index work limits; the complete output is reparsed for combined bounds.

There is one instrumented source parse and a full result parse; set additionally
parses its replacement as exactly one value. Statement ancestor checks are at
most64 steps, and insertion selects a header in at most64 statement scans.
Memory grows with bounded document arenas, statement spans and owned output.
The editor does no I/O, native allocation tricks, recursion of its own or
cryptography. It does not edit inside inline tables or index arrays, and does
not replace a declared table with an inline value.

Full-call benchmark samples and compiler/platform/binary/source provenance are
in [the benchmark record](../bench/results/2026-11-04/README.md). No timing gate,
competing-library ranking or universal throughput claim is made.

## Consumer-overload hardening follow-up (release gated)

The immutable parser/ownership fix approved by the TOML primary is
`c32c7dab44883f8fb5a5a984bf6f3c4c49119d79`. This follow-up tests that exact
snapshot on a feature branch. It is not approval of a whole-library alpha,
the outstanding numeric-writer changes, or a new Honk pin. Honk's merge remains
held until the primary delivers its final approved post-release/source-merge SHA.
The editor's parser and quoted-key helper coupling is specific to a reviewed pin.

With that parser fix present, a public consumer defining a builder `copy`
overload still caused the original editor to return an empty successful edit.
The dedicated regression failed its exact-output assertion before the editor
fix. All editor-owned diagnostics, error/output copies and replacement wrapper
construction now use built-in byte appends through `toml_edit::owned`.

The regression root defines string, copying, numeric conversion, integer
formatting and index-sizing overloads. It checks exact source/output preservation,
malformed source and fragment rejection, error positions, UTF-8 and size bounds,
unsupported paths, aliasing, independent ownership and rehashing. It is wired
into interpreted, optimized, debug/no-BCE and generated-C sanitizer targets.
Final release measurements and dependency promotion wait for the approved pin.

Scoped follow-up evidence: `make format check test property` passed; overload
regressions passed interpreted, optimized and debug/no-BCE execution. Full GCC
and Clang ASan/UBSan targets passed, including overload/boundary/smoke tests and
207 oracle calls per toolchain with leak detection enabled. Two independent
reviewers found no remaining blocker in this scoped change, verified all vendor
bytes against the exact approved parser commit, and independently reran the
consumer regressions. One reviewer also repeated3,032 scanner/parser parity
cases successfully. This evidence does not clear the outstanding upstream
writer/alpha/source merge or Honk release gates.
