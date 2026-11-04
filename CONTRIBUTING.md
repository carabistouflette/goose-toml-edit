# Contributing

Keep the public API small, bounded and pure. Reuse the pinned TOML parser;
never introduce a second decoder. Preserve bytes outside selected edit spans,
owned output and failure atomicity. Add public API regressions for behavior
changes, malformed input, ownership and limits.

Use focused branches and Conventional Commits with imperative subjects:
feat:, fix:, test:, docs:, perf:, chore:. Commit working milestones regularly.
Request independent correctness/security and quality/performance reviews at
design and implementation checkpoints; resolve findings before release.
Run make format check test property sanitize and git diff --check. Measure full
public calls before optimizing, preserve raw samples, compiler/platform/build
provenance and report regressions. CI checks execution, not timing thresholds.
Never commit build output, credentials or private notes. Update pinned vendor
snapshots deliberately; keep exact hashes, licenses and provenance. Compiler
changes require a full reviewed revision and complete validation.
