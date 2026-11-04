# Release verification

Run the read-only verifier from a checkout containing the release and trusted
tested-head Git objects. It uses Python's standard library and Git, performs no
extraction, and changes no tags, refs, source files or dependencies.

```sh
python3 scripts/verify-release.py --tag v0.1.0 \
  --expected-commit ae32f13d69b69c9604a44d7acd71d2f966daef35 \
  --tested-head b9b6ab1b8d9defb9c296891d57311a2162ebddb7 \
  > /tmp/release-verification.json
```

By default the repository is `carabistouflette/goose-toml-edit`, and Git objects
come from this checkout. Use `--repo OWNER/NAME` and `--git-repo PATH` to change
those explicit inputs. Fetch missing objects yourself before verification; the
tool does not silently fetch or advance refs. A shallow checkout must contain
both full commit IDs. Git replacement refs are disabled for all object queries.

Live mode reads public GitHub release/tag metadata and the tag archive over
direct HTTPS, with proxies disabled, redirects rejected and a 30-second timeout per request. This is not
an overall wall-clock deadline. No credentials are requested or sent by the
tool. GitHub's anonymous API rate limits apply. Lightweight and annotated tags
are supported, with annotated chains limited to eight objects. Releases must be
nondraft prereleases; `--stable` instead requires a stable nondraft release.

## What passes

- The public tag resolves to the explicit expected commit, and its tree equals
  the explicit tested-head tree. Both anchors must be full lowercase SHA-1
  commit IDs available in the local repository.
- All archive files match the anchored Git blob IDs and executable bits. The
  archive has one root, safe unique paths, ordinary files/directories only,
  complete gzip CRC/footer and tar end markers, and no hidden trailing payload.
  Privilege bits and mode values outside ordinary POSIX permissions are rejected.
- The root wrapper, license, compiler revision and vendor manifest are present
  and nonempty. The compiler revision and vendor revisions are full commit IDs.
  Every library has a license record/file, every declared SHA-256 matches, and
  no unlisted files exist beneath `vendor/`.
- Build/toolchain/Git/cache directories and Python bytecode are absent. This
  checks known generated-state paths, not arbitrary filename-based provenance.

Limits are 32 MiB compressed, 128 MiB expanded before tar parsing, 16 MiB per
file, 8,192 exposed tar entries, 1,024 characters per path and 1 MiB per metadata
response/offline bundle. Duplicate JSON keys and malformed records fail closed.
These are verifier limits, separate from the editor's runtime input limits.

Only successful verification emits JSON to stdout. Failures return nonzero and
write a diagnostic to stderr, including under `python3 -O`. The result records
the metadata mode, metadata/archive SHA-256, anchors, tree, compiler revision
and verified vendor library identities/file hashes. Historical releases are checked against their
anchored archive contents, never the current checkout's runtime/vendor files.

## Offline evidence and CI

Use both `--metadata bundle.json --archive release.tar.gz` to verify retained
inputs without network access. The bundle has `release` and `tag_ref` objects
matching the public GitHub REST responses. `annotated_tags` maps each annotated
tag object SHA to its REST response; it can be empty for lightweight tags.

Offline results are labeled `metadata_mode: offline`; they are not fresh GitHub
observations. The metadata hash covers the supplied bundle bytes in offline
mode and the sorted compact JSON bundle in live mode. Retain both inputs with
the result for reproduction. This script checks identity/content, not signatures,
publisher authority, CI execution or approval. The tested-head anchor must come
from separately trusted test/CI evidence. Vendor checks establish consistency
with the committed manifest; upstream Git-object publication audits remain a
separate responsibility. License checks verify presence and bytes, not legal
interpretation.

`make check` and the early CI step run hermetic fixtures without network access.
They cover valid lightweight/annotated tags, wrong identities, replacement refs,
modified/missing/extra files, executable modes, unsafe/PAX/duplicate paths,
mixed roots, links/sparse/special entries, decompression limits, truncated gzip,
hidden appended archives, malformed vendor/license/compiler records and
optimized-Python CLI failure. Run them directly with:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```
