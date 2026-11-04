// SPDX-License-Identifier: Apache-2.0
import toml_edit from "..";
import toml from "../vendor/goose-toml";
import std;
import os;
fn main() {
    let argv = args(); assert(argv.len == 3);
    let count, ok = parse_int(argv[2]); assert(ok && count >= 1 && count <= 10000);
    let name = argv[1];
    var source = str("# package\n[package]\nname = 'hello'\n[dependencies]\ntext = { path = '../text' } # keep\n");
    var path: const u8[:][>..] = []; path.push("dependencies"); path.push("text");
    let removing = name == "remove";
    if name == "insert" { path.clear(); path.push("dependencies"); path.push("new"); }
    if name == "wide" {
        source.clear(); for i in 10000 { source.append(str("key", i, " = ", i, " # keep\n")); }
        path.clear(); path.push("key5000");
    }
    if name == "deep" {
        source = str("["); path.clear();
        for i in 63 { if i > 0 { source.push('.'); } source.push('a'); path.push("a"); }
        source.append("] # deep\nx=1\n"); path.push("new");
    }
    if name == "comments" {
        source = str("x=1\n#"); for i in 1000000 { source.push(' '); }
        path.clear(); path.push("x");
    }
    assert(name == "set" || name == "insert" || removing || name == "wide" || name == "deep" || name == "comments");
    let replacement = if name == "set" || name == "insert" { "{ path = '../new' }" } else { "42" };
    var out: u8[>..] = []; var checksum: i64 = 0;
    let start = clock_ns();
    for _ in count {
        let error = if removing { toml_edit::remove(source, path, out) } else { toml_edit::set(source, path, replacement, out) };
        assert(error.len == 0 && out.len > 0);
        checksum += out.len + out[0] + out[out.len - 1];
    }
    print(clock_ns() - start, " ", checksum);
}
