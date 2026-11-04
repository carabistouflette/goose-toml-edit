# Legacy editor contract

`legacy-cedb2c3.json` is the unchanged 21-case artifact captured from the clean
`cedb2c3c98affbeb45bd34bc7a6618f5a9b75ad0` companion implementation before the
canonical compatibility profile was implemented. Its SHA-256 is
`f137e22aec1276deb6728fd261d77ece3f76c5eac1de6d7cb0dde804b9f50fbd`.

The property campaign verifies the artifact hash and compares status, output
bytes and diagnostic bytes. Expected results must come from the preserved
legacy oracle, never from the candidate. Two additional fragment diagnostics
in `frozen_legacy` were independently replayed against that same legacy binary.
Direct Goose tests cover aliases, empty paths, invalid UTF-8 and NUL keys that
the file/argv driver cannot express.

To compare a canonical checkpoint without adopting its vendor files:

```sh
python3 scripts/property-test.py --runner .build/consolidation-legacy-driver \
  --canonical-oracle /absolute/path/to/isolated/source/.build/oracle --cases 5000
```

The optional canonical runner uses the source owner's LS/LR tab-separated hex
protocol. Every call compares complete results and rejects crashes, stderr and
failure output. Binary hashes are checked before and after the campaign; retain
the separately verified build provenance to associate binaries with commits.
Checkpoint evidence is recorded in `docs/results/canonical-5cca023-parity.json`.
