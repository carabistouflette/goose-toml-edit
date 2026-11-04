// SPDX-License-Identifier: Apache-2.0
import toml_edit from "..";
import toml from "../vendor/goose-toml";
import std;
fn reject(source: u8[:], path: const u8[:][:], value: u8[:]) {
    var out = str("stale");
    assert(toml_edit::set(source, path, value, out).len > 0 && out.len == 0);
}
fn main() {
    for key in ["\x7f", "\0", "\t\r\n", "quote\"slash\\", "é😀", "", "a.b"] {
        var out: u8[>..] = [];
        assert(toml_edit::set("", [key], "1", out).len == 0);
        var doc = toml::Document { .. };
        assert(toml::parse_into(out, doc).len == 0);
        let node = toml::find(doc, 0, key); assert(node >= 0 && doc.nodes[node].integer == 1);
        assert(toml_edit::set(out, [key], "2", out).len == 0);
        assert(toml_edit::remove(out, [key], out).len == 0 && out == "\n");
    }
    var out: u8[>..] = [];
    let empty_path: const u8[:][] = []; reject("x=1", empty_path, "2");
    var path: const u8[:][>..] = []; for i in 65 { path.push("x"); } reject("", path, "1");
    var limit = str("#"); for i in toml_edit::MAX_INPUT_BYTES - 1 { limit.push(' '); }
    assert(toml_edit::remove(limit, ["missing"], out).len == 0 && out == limit);
    reject(limit, ["x"], "1"); limit.push(' '); reject(limit, ["x"], "1");
    var deep = str(""); for i in 64 { deep.push('['); } deep.push('1'); for i in 64 { deep.push(']'); }
    reject("", ["x"], deep);
    var source = str("x=1");
    assert(toml_edit::set(source, ["x"], "2", out).len == 0);
    source[0] = 'y'; assert(out == "x=2");
    assert(toml_edit::set(out, ["x"], "invalid", out).len > 0 && out.len == 0);
    for sample in ["", "# c\r\n", "x=1", "x=\"unterminated", "[x]\nx=1\n", "x=1\nx=2", "\xff", "x='''\n[a]\n'''", "x=[1, # c\n 2]", "[[a]]\nx=1", "x=1\r", "# bad\x01", "x={a.b=1}"] {
        var doc = toml::Document { .. };
        let expected = toml::parse_into(sample, doc);
        var checked: u8[>..] = [];
        let error = toml_edit::remove(sample, ["__missing__"], checked);
        assert((expected.len == 0) == (error.len == 0));
        assert(if error.len == 0 { checked == sample } else { checked.len == 0 });
    }
    print("boundary and parser parity tests passed");
}
