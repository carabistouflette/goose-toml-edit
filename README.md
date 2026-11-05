# goose-toml-edit

Change named values in TOML 1.0 while keeping comments and untouched formatting.
Pure Goose, Apache-2.0, experimental API. Applications handle file I/O and atomic
saving; this library edits bytes in memory.

The latest release is [v0.1.1](https://github.com/carabistouflette/goose-toml-edit/releases/tag/v0.1.1),
a prerelease. Main has the same editor and pinned TOML engine, plus later release-
verification tooling and documentation. There is no API stability promise yet.

## Try it

With Git, Make, Python 3.11+, CMake 3.27+ and a C++20 toolchain installed:

```sh
git clone https://github.com/carabistouflette/goose-toml-edit.git
cd goose-toml-edit
make setup
.toolchain/goose/build/goose run examples/dependency.goose
```

The [example](examples/dependency.goose) inserts a dependency beneath
`[dependencies]` and keeps the existing comment. Setup builds the exact compiler
in `GOOSE_REVISION`. You can instead use an existing compiler at that revision.
There are no native runtime dependencies specific to this library. Current CI
covers Linux; sanitizer targets require GCC/Clang.

## API

- `set(source, decoded_path, raw_value, out)` replaces an assignment's value or
  inserts a missing key. The value must be one complete TOML value.
- `remove(source, decoded_path, out)` removes the selected assignment or table
  subtree. A missing key succeeds with an owned copy of the original source.

Both return an owned error string, empty on success, and replace `out`.
Failure clears `out`. Inputs may borrow from `out` during the call; replacing
output can then overwrite that shared storage. Path components are decoded keys:
a dot inside one component is literal.
See the [API and import guide](docs/api.md) for a complete example and contracts.

Source/output are limited to 1 MiB, paths to 64 components and 1 MiB combined
key bytes. Parser limits also apply. Individual array elements, children inside
inline tables, and replacing a header-declared table with a value are unsupported.
Insertion has a conservative key-encoding limit described in the API guide.

The editor delegates to the pinned [goose-toml](vendor/manifest.json) source
engine; it does not contain another parser. The recorded engine revision is
`fe849141405009e36e1cce6eb479b395eae18f1a` (upstream alpha.3). Use exact compatible
pins when supplying the required root `toml` import mapping.

## Development

Run `make check test property` after setup. See [validation](docs/validation.md),
[measurements](bench/README.md), [security reporting](SECURITY.md), and the
[release verifier](docs/release-verification.md). The [v0.1.1 receipt](docs/results/release-v0.1.1.md)
links release and Honk acceptance details separately from the API documentation.
