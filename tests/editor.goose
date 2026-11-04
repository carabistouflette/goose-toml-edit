// SPDX-License-Identifier: Apache-2.0
import toml_edit from "..";
import toml from "../vendor/goose-toml";
import std;
fn main() {
    var out: u8[>..] = [];
    assert(toml_edit::set("# keep\n[a] # table\nx = 1 # value\n", ["a", "x"], "2", out).len == 0);
    assert(out == "# keep\n[a] # table\nx = 2 # value\n");
    assert(toml_edit::set(out, ["a", "y"], "true", out).len == 0);
    assert(out == "# keep\n[a] # table\n\"y\" = true\nx = 2 # value\n");
    assert(toml_edit::remove(out, ["a", "x"], out).len == 0);
    assert(out == "# keep\n[a] # table\n\"y\" = true\n # value\n");
    // Compute the whole result before mutating any caller-owned alias.
    out.clear(); out.append("42");
    assert(toml_edit::set("x=1", ["x"], out, out).len == 0 && out == "x=42");
    out.clear(); out.append("borrowed.key");
    let insert_key: const u8[:] = out;
    assert(toml_edit::set("", [insert_key], "1", out).len == 0);
    assert(out == "\"borrowed.key\" = 1\n");
    out.clear(); out.append("x");
    let remove_key: const u8[:] = out;
    assert(toml_edit::remove("x=1\ny=2", [remove_key], out).len == 0 && out == "\ny=2");
    out.clear(); out.append("1 # suffix");
    let error = toml_edit::set("x=1", ["x"], out, out);
    assert(out.len == 0);
    out.append("reused storage");
    assert(error == "toml-edit: replacement must be exactly one value without a trailing comment or newline");
    out.clear(); out.append("\xff");
    let invalid_key: const u8[:] = out;
    let path_error = toml_edit::set("", [invalid_key], "1", out);
    assert(out.len == 0 && path_error == "toml-edit: invalid or oversized key path");
    assert(toml_edit::set("", ["\0"], "1", out).len == 0 && out == "\"\\u0000\" = 1\n");
    print("editor tests passed");
}
