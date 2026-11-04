// SPDX-License-Identifier: Apache-2.0
import toml_edit from "..";
import toml from "../vendor/goose-toml";
import std;
fn main() {
    var out: u8[>..] = [];
    let error = toml_edit::set("# keep\n[dependencies]\n", ["dependencies", "text"], "{ path = '../goose-text' }", out);
    assert(error.len == 0);
    print(out);
}
