// SPDX-License-Identifier: Apache-2.0
import toml_edit from "..";
import toml from "../vendor/goose-toml";
import std;
import os;
fn main() {
    let argv = args(); assert(argv.len >= 6);
    var source: u8[>..] = []; var value: u8[>..] = []; var out: u8[>..] = [];
    assert(read_file(argv[2], source)); assert(read_file(argv[3], value));
    var path: const u8[:][>..] = [];
    for part in argv[5..] { path.push(part); }
    let error = if argv[1] == "set" { toml_edit::set(source, path, value, out) }
        else { toml_edit::remove(source, path, out) };
    if error.len > 0 { assert(out.len == 0); print(error); exit(1); }
    assert(write_file(argv[4], out));
}
