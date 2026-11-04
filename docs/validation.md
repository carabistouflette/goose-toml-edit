# Validation and limits

## Canonical engine adapter

The companion delegates to supported `toml_source::legacy_set` and
`legacy_remove` in immutable canonical pin
`fe849141405009e36e1cce6eb479b395eae18f1a` (upstream `v0.1.0-alpha.3`).
The adapter waits for the complete owned `(output, error)` pair, then clears and
appends into the caller's output. It contains no scanner, lookup, key encoder,
fragment parser or fallback engine. Existing public signatures, constants,
diagnostic bytes, precedence and aliasing remain the compatibility contract.

The canonical editor blob matches reviewed checkpoint
`a79cf60ff6ba86dd887dd5749f5b312ca0ef48b4`, SHA-256
`1fa20fcb1bb3c7ad1751788ae34d6c91dd348397e8871283da6c687c222b59c1`.
Only that editor changes from the prior nine-file vendor snapshot. All eight
other files, including core, licenses and source README, remain byte-identical.
The adapter, public API, bounds and error contract remain unchanged.

The approved upstream merge does not share the complete tested-head tree.
Only root README/CHANGELOG differ from tested
`debe1ab0fc6a99b5db41d308fb302aa9a925bbb2`, exactly matching approved docs parent
`70fb784417798742394e15629d246d3c42a5724d`. Runtime/editor/oracle identities are
verified separately; the generic release verifier's strict tree check is not
weakened or presented as validating that upstream docs bridge.

The isolated `ae32` adapter overlay passed eight unchanged direct execution modes
and GCC/Clang ASan/UBSan, with 234 property calls each, on the identical editor
and core/test bytes. This explicit runtime identity bridge does not substitute
for fresh pinned-wrapper checks, new-head CI or Honk consumer acceptance.
The real snapshot receives those gates before a later companion release.

Qualified [upstream experiment evidence](https://github.com/carabistouflette/goose-toml/blob/fe849141405009e36e1cce6eb479b395eae18f1a/source/tests/results/document-reuse/README.md)
retains all series, controls, duration eligibility and the unreproduced outlier.
Region counts are fixture-specific; RSS describes whole processes. Neither
establishes per-call allocation savings or a universal speedup. No new timing
campaign accompanies this update. Published alpha.3 approval supersedes the
retained experiment's historical pre-promotion hold.

### Original v0.1.0 consolidation evidence

The unchanged 21-case legacy artifact is checked by SHA-256 before each property
campaign. It was captured from clean companion `cedb2c3`, before canonical profile
implementation. Exact errors and outputs come from that baseline, never from
candidate output. Both the original checkpoint and final engine passed full
status/output/error differential checks; retained provenance and results are in
[the final engine record](results/canonical-04c8bef-parity.json). Direct Goose
tests additionally exercise source/value/path aliases with output, returned error
ownership, NUL keys, empty paths, exact decoded-path limits and conservative
sixfold key-rendering limits.

The original released adapter passed a direct 5,134-call comparison against the preserved
legacy binary, including exact output and error bytes. Standard checks passed 494
property calls plus direct JIT/O2/debug alias/overload/boundary tests. GCC and
Clang ASan/UBSan each passed the direct suites plus 234 property calls. A clean Git
export passed checks/tests/property without sibling dependencies. Two independent
wrapper/vendor/harness reviews found no remaining blockers; every vendored byte
was compared against the public immutable Git objects. Full provenance is in
[the adapter validation record](results/adapter-de7dfe0-validation.json).

[Paired full-call timing records](../bench/results/canonical-adapter/README.md)
retain both the initial short-loop series and its longer-loop confirmation.
They expose shared-host/run sensitivity and a comment-heavy slowdown in both
series. These measurements support no universal speedup claim.

## Original implementation validation

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
parses its replacement as exactly one value. Canonical lookup walks sibling
lists, removal selects descendants with a node bitmap, and insertion records
header contexts before selecting an anchor. Terminal result parsing reuses the
Document only after all original edit metadata is consumed. Parser work limits
remain unchanged. Storage grows with bounded document arenas, statement spans,
selection/context buffers and owned output; no strict allocation-byte budget
or per-call memory-saving claim is made.
The editor does no I/O, native allocation tricks, recursion of its own or
cryptography. It does not edit inside inline tables or index arrays, and does
not replace a declared table with an inline value.

Full-call benchmark samples and compiler/platform/binary/source provenance are
in [the benchmark record](../bench/results/2026-11-04/README.md). No timing gate,
competing-library ranking or universal throughput claim is made.

## Consumer-overload hardening follow-up

The hardening was first validated against the primary's approved parser/ownership
fix `c32c7dab44883f8fb5a5a984bf6f3c4c49119d79`, while its separate numeric-writer
and source-module gates were held. The dependency approved for that hardening was the
immutable source-merge commit `c1c703f8dd4ac4e0ebc95f35981e87becad76957`.
The primary explicitly cleared the earlier alpha-ordering hold for this handoff;
no alpha release is claimed or required for this pin.

Published merge and tested head `cfeef473ab8886832f9d41f6e122a3c85bae4e37`
share tree `5afd3559c04d65aa4bc29468db4d0d7398be7fa2`. Exact-head root/source
checks passed on x86 and ARM64 in runs41879137478,41879128955,41879137484 and
41879128925. Post-merge duplicate runs are not used as terminal evidence here.
The parser/document/text sources, writer context, bounded writes and quoted-key
encoder match the approved compatibility baseline. That implementation used
private parser helpers. The canonical adapter above supersedes that private
seam; its engine remains tied to the immutable parser snapshot.

With that parser fix present, a public consumer defining a builder `copy`
overload still caused the original editor to return an empty successful edit.
The dedicated regression failed its exact-output assertion before the editor
fix. That implementation changed all editor-owned diagnostics, error/output
copies and replacement wrapper construction to built-in byte appends through
`toml_edit::owned`. The canonical adapter subsequently removed that helper along
with the duplicated engine.

The regression root defines string, copying, numeric conversion, integer
formatting and index-sizing overloads. It checks exact source/output preservation,
malformed source and fragment rejection, error positions, UTF-8 and size bounds,
unsupported paths, aliasing, independent ownership and rehashing. It is wired
into interpreted, optimized, debug/no-BCE and generated-C sanitizer targets.
Initial benchmark records retain their measured historical revisions; no speedup
is claimed for this correctness hardening.

Scoped follow-up evidence: `make format check test property` passed; overload
regressions passed interpreted, optimized and debug/no-BCE execution. Full GCC
and Clang ASan/UBSan targets passed, including overload/boundary/smoke tests and
207 oracle calls per toolchain with leak detection enabled. Two independent
reviewers found no remaining blocker in this scoped change, verified all vendor
bytes against the exact approved parser commit, and independently reran the
consumer regressions. One reviewer also repeated3,032 scanner/parser parity
cases successfully. The subsequent immutable upstream handoff clears its dependency gate; Honk
still receives separate combined consumer validation before merge.
