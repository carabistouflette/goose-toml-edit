# goose-toml-edit

A bounded, comment-preserving TOML 1.0 editor in pure Goose. Experimental API,
Apache-2.0. Applications own filesystem I/O and atomic publication.

```goose
import toml_edit from "../goose-toml-edit";
import toml from "../goose-toml-edit/vendor/goose-toml";
import std;
fn main() {
    var out: u8[>..] = [];
    let error = toml_edit::set("[dependencies]\n", ["dependencies", "text"],
        "{ path = '../goose-text' }", out);
    assert(error.len == 0);
    print(out);
}
```

Goose requires dependency mappings in the application's root file. Map `toml`
to the pinned snapshot here, or to the identical reviewed upstream revision in
[vendor/manifest.json](vendor/manifest.json). The editor intentionally couples
to that parser's internal helpers to record source spans without introducing a
second TOML decoder. Dependency updates require the complete validation suite.

`set(source, decoded_path, raw_value, out)` replaces a complete assignment or
inserts a missing key. Path components are decoded keys: dots within a component
are literal. `remove(source, decoded_path, out)` removes assignments and table
headers in that subtree; missing keys are a successful no-op. Both return an
owned error string, empty on success, and replace `out`. Failure clears `out`;
source is untouched. Output owns its bytes; source may alias `out` during a call.

Existing assignment replacement changes only its value token. Removal deletes
only declaration syntax, retaining indentation, trailing comments, newlines and
standalone comments. Comments inside a replaced/removed value belong to that
value and are removed. Insertion uses the closest explicit ancestor header,
otherwise root scope, and emits quoted keys with the first original newline
style (LF when there is none). All other original bytes remain unchanged.

Replacing a declared table with an inline value, navigation through arrays or
inside inline tables is unsupported and returns an error. A complete inline
assignment can be replaced or removed. Arrays of tables elsewhere in the file
are preserved. Invalid inputs and replacement suffix comments/newlines/extra
statements are rejected. Internal newlines inside arrays/strings are supported.

Source and output are capped at 1 MiB; decoded paths at 64 components and 1 MiB
combined bytes. Insertion reserves six encoded bytes per key byte; this can
conservatively reject large plain keys before actual output reaches the cap. The pinned parser additionally bounds nodes, depth and key-index
work. Complete result validation enforces combined limits and TOML declaration
rules before returning output. There are no runtime native dependencies.

Run `make setup` for the pinned compiler, then `make format check test property`.
`make sanitize SANITIZER_CC=gcc` and `SANITIZER_CC=clang` instrument generated C,
including the Goose runtime; test integration and source checks also run in CI.
There are no releases or stability promises yet.
