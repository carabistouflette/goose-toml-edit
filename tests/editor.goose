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
    print("editor tests passed");
}
