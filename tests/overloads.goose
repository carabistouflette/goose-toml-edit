// SPDX-License-Identifier: Apache-2.0
// Application convenience overloads must not erase errors or owned output.
import toml_edit from "..";
import toml from "../vendor/goose-toml";
import std;
fn str(value: const u8[:]) -> u8[>..] { [] }
fn str(a: const u8[:], b: const u8[:]) -> u8[>..] { [] }
fn str(a: const u8[:], b: const u8[:], c: const u8[:], d: i64,
       e: const u8[:], f: i64, g: const u8[:], h: i64, i: const u8[:]) -> u8[>..] { [] }
fn str(value: f64) -> u8[>..] { [] }
fn str(value: i64) -> u8[>..] { [] }
fn format(out: u8[>..]&, value: i64) { out.append("invalid"); }
fn copy(value: u8[>..]&) -> u8[>..] { [] }
fn copy(value: i64[>..]&) -> i64[>..] { [] }
fn parse_int(value: const u8[:]) -> i64, bool { return 123, true; }
fn parse_int(value: u8[>..]&, base: i64) -> i64, bool { return 2, true; }
fn parse_flt(value: u8[>..]&) -> f64, bool { return 2.0, true; }
fn max(a: i64, b: i64) -> i64 { 16 }
fn rejected(source: const u8[:], path: const u8[:][:], value: const u8[:], removing: bool = false) {
    var out: u8[>..] = []; out.append("stale");
    let error = if removing { toml_edit::remove(source, path, out) }
        else { toml_edit::set(source, path, value, out) };
    assert(error.len > 0 && out.len == 0);
}
fn main() {
    var out: u8[>..] = [];
    assert(toml_edit::set("x=1 # keep", ["x"], "2", out).len == 0);
    assert(out == "x=2 # keep");
    assert(toml_edit::set(out, ["y"], "1.25", out).len == 0);
    assert(out == "\"y\" = 1.25\nx=2 # keep");
    assert(toml_edit::remove(out, ["x"], out).len == 0);
    assert(out == "\"y\" = 1.25\n # keep");
    assert(toml_edit::remove(out, ["missing"], out).len == 0 && out == "\"y\" = 1.25\n # keep");
    for source in ["v=[1", "v=01", "v=", "v=9223372036854775808", "v=1e99999", "v=1.", "v=0x8000000000000000", "v=1\nv=2", "\xff"] {
        rejected(source, ["x"], "1"); rejected(source, ["x"], "", true);
    }
    for value in ["", "[1", "01", "9223372036854775808", "1e99999", "1\ninjected=2", "1 # suffix", "\xff"] {
        rejected("x=1", ["x"], value);
    }
    rejected("", ["\xff"], "1");
    assert(toml_edit::remove("v=[1", ["missing"], out) == "toml: unexpected delimiter at byte 4 (line 1, byte column 5)");
    assert(out.len == 0);
    let empty_path: const u8[:][] = [];
    rejected("x=1", empty_path, "2");
    rejected("x={y=1}", ["x", "y"], "2");
    rejected("[x]\ny=1", ["x"], "2");
    rejected("x=1", ["x", "y"], "2", true);
    var huge: u8[>..] = []; for _ in toml_edit::MAX_INPUT_BYTES + 1 { huge.push(' '); }
    rejected(huge, ["x"], "1"); rejected("x=1", ["x"], huge);
    var source: u8[>..] = []; source.append("#");
    for _ in toml_edit::MAX_INPUT_BYTES - 1 { source.push(' '); }
    rejected(source, ["x"], "1");
    source.clear();
    let keys = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t"];
    for key in keys { source.append(key); source.append("=41\n"); }
    assert(toml_edit::set(source, ["k"], "1.25", out).len == 0);
    var doc = toml::Document { .. }; assert(toml::parse_into(out, doc).len == 0);
    for key in keys {
        let id = toml::find(doc, 0, key); assert(id > 0);
        if key == "k" { assert(doc.nodes[id].kind == toml::Kind.Float && doc.nodes[id].number == 1.25); }
        else { assert(doc.nodes[id].integer == 41); }
    }
    source[0] = 'z'; assert(out[0] == 'a');
    assert(toml_edit::set(out, ["k"], "[1", out).len > 0 && out.len == 0);
    print("editor consumer-overload regressions passed");
}
