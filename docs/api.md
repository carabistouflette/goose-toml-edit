# API and imports

The public API is `set`, `remove`, `MAX_INPUT_BYTES` (1,048,576) and
`MAX_DEPTH` (64 decoded path components). `MAX_DEPTH` is a path limit, not the
parser's TOML nesting limit. Applications own I/O, repeated-call budgets and
atomic saving after success.

## Root import mapping

For a sibling checkout, a complete application is:

```goose
import toml_edit from "../goose-toml-edit";
import toml from "../goose-toml-edit/vendor/goose-toml";
import std;
fn main() {
    var out: u8[>..] = [];
    let error = toml_edit::set("# keep\n[dependencies]\n",
        ["dependencies", "text"], "{ path = '../goose-text' }", out);
    assert(error.len == 0);
    print(out);
}
```

Goose requires the `toml` dependency mapping in the application's root source.
Use the snapshot above or the identical upstream revision from
[the manifest](../vendor/manifest.json). For remote dependencies the matching
published imports are:

```goose
import toml_edit from "carabistouflette/goose-toml-edit@f8d1b1664a86b768a6f1375636d9b2c3a440aa31";
import toml from "carabistouflette/goose-toml@fe849141405009e36e1cce6eb479b395eae18f1a";
```

The companion delegates to supported `toml_source::legacy_set` and
`legacy_remove`. The pinned engine handles parsing, validation and edit policy.
The adapter finishes the owned result before replacing output, so consumer
`str`/`copy` overloads do not change its ownership or diagnostics.

## Edits and byte preservation

`set(source, decoded_path, raw_value, out)` replaces an existing assignment's
value token or inserts a missing key. Path components are decoded UTF-8 keys,
not dotted strings or array indices. `["a.b", "c"]` means literal key `a.b`,
then child `c`. Empty keys are supported; the path itself must be nonempty.
The replacement keeps its raw spelling. Only spaces/tabs may follow its value;
suffix comments, newlines and extra statements are rejected. Comments/newlines
inside an array or string value remain valid TOML.

`remove(source, decoded_path, out)` removes declarations in that subtree,
including table headers and their values. After input validation, an absent
path prefix succeeds with an owned copy. Traversal through a scalar, array or
inline table fails even when the requested child is missing.
A whole array of tables can be removed, but individual elements cannot be
selected. Removing the last dotted child may also remove its implicit parent
semantically; no explicit empty table is inserted.

Replacement changes only the selected value token. Removal keeps indentation,
trailing comments, newlines and standalone comments outside removed declarations.
Comments inside a removed/replaced value are part of that value and disappear.
Insertion starts at root byte zero or after the closest explicit ancestor header's
complete line. It emits quoted keys using the first source newline style (LF
when absent). Other original bytes stay unchanged; orphan comments are not moved.

Replacing a declared table with an inline value, traversal through arrays or
inside inline tables returns an error. A complete directly assigned inline
value can be replaced or removed. Unsupported layouts do not fall back to
whole-document reformatting. Batch edits and formatting cleanup are not provided.

## Ownership, errors and limits

Both operations return an owned error string: empty on success, nonempty on
failure. They replace `out`; failure clears it. Source, value and borrowed path
components may alias `out` during a call. Returned output/error own their bytes.
Validation order is path, replacement fragment (for set), then original source.
The complete result is validated before success.

- Source and output: at most 1 MiB each.
- Replacement: nonempty, at most 1 MiB minus the four-byte `x = ` parse wrapper.
- Path: 1..64 components, valid UTF-8, at most 1 MiB combined decoded bytes.
- Insertion reserves two quote bytes plus six bytes per decoded key byte, with
  prior separators counted. This may reject a large plain key whose actual
  encoding would fit. It does not apply to replacing an existing assignment.
- The pinned parser additionally bounds nodes, nesting and key-index work.
  Allocation failure follows the Goose runtime policy; these are not an RSS or
  wall-clock guarantee.

See [validation](validation.md) for test scope and [measurements](../bench/README.md)
for repeated-call cost and recorded source identities.
