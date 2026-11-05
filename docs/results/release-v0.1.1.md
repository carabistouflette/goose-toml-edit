# v0.1.1 publication and consumer acceptance

The experimental [v0.1.1 release](https://github.com/carabistouflette/goose-toml-edit/releases/tag/v0.1.1)
is published as a nondraft prerelease at
`f8d1b1664a86b768a6f1375636d9b2c3a440aa31`, with canonical TOML pinned to
`fe849141405009e36e1cce6eb479b395eae18f1a` (upstream alpha.3).
Publication and Honk adoption are complete. This receipt records completed
checks; it does not introduce another acceptance campaign or performance claim.

The [candidate validation snapshot](adapter-fe849-validation.json) is retained
unchanged. Its `consumer_acceptance` entry describes the earlier pending stage,
before the acceptance and publication recorded below.

## Released identity and evidence

[Companion PR #3](https://github.com/carabistouflette/goose-toml-edit/pull/3)
merged tested and accepted head `44c99adbe3659877527fe84022db9481262412f2`.
The accepted head and released commit have the identical complete tree
`a2a9534d317539ab801afd6ba1313abc70fe6e84`.
Both exact-head [PR CI](https://github.com/carabistouflette/goose-toml-edit/actions/runs/41930125849)
and [push CI](https://github.com/carabistouflette/goose-toml-edit/actions/runs/41930099183)
completed successfully.

The public [release-verification asset](https://github.com/carabistouflette/goose-toml-edit/releases/download/v0.1.1/release-verification-v0.1.1.json)
records tag/archive/vendor verification and separately identified owner gate
evidence, including the isolated consumer acceptance. Its SHA-256 is
`bba087358407f7b83e6d1e52fb885101a12b41d5c2d9f89ab6fae56f4996d4ed`;
the verified 48-file release archive SHA-256 is
`700127e0344cef8651b339fb8e76292843d5ed11ae759e502ed9055d757d8122`.
These digests identify the artifacts; they are not signatures or independent
proof of testing. See the [verifier's scope](../release-verification.md).

The upstream identity bridge is different: tested canonical head
`debe1ab0fc6a99b5db41d308fb302aa9a925bbb2` to released `fe849141` differs only
in root README/CHANGELOG, matching approved docs parent
`70fb784417798742394e15629d246d3c42a5724d`. Full upstream tree identity is not
claimed. Runtime/editor/oracle bytes match the tested head, as recorded in the
candidate snapshot and release asset.

## Original isolated consumer acceptance

The Honk owner accepted exact companion head `44c99ad` and canonical `fe849141`
in an isolated public clone of Honk
`f12d88a774760e7fbfd4f5ad6e03e15b7e5e392a`, with only the dependency graph
changed. This acceptance excluded the then-separate SIGPIPE correction.

The owner reported passing check/build, five manifest-edit methods, seven Git
workflow methods, and normal/frozen self-check and package commands. The lock
remained byte-identical; normal/frozen package bytes matched, all 15 required
dependency/manifest/license files were compared across 127 exports, and
generated state was absent. The release asset retains the acceptance details:

- Acceptance report SHA-256:
  `02481fc40da5da292b7d3389be2d8d17f529fab21f63bb028eb6061fbe17056e`.
- Consumer patch SHA-256:
  `7506a6603cc953a49e1bc7c7756d1b9e2d1c9844405f19961fb339edeb41f8a7`.
- Accepted consumer index tree:
  `f57e1cf710d3120cf8fb4ddb11a82c10dbaf38a8`.

## Final combined Honk adoption

Honk subsequently published the released companion/canonical pins at
`b8bf23641596fdc7abb6b6959ac660063cafa586`, through guarded fast-forward
[Honk PR #3](https://github.com/carabistouflette/honk/pull/3) from the separate
SIGPIPE corrective checkpoint `ce7995d10c9528fcf997307dea5e4e2fba0c7b2c`.
The tested/public tree is `2d8dcc5f5b92d0a154a7f788ab3f0a689c5e9af8`.
Both GCC/Clang jobs in exact-source [push CI](https://github.com/carabistouflette/honk/actions/runs/41937064200)
and [PR CI](https://github.com/carabistouflette/honk/actions/runs/41937135619)
completed successfully; duplicate main runs are not used as evidence here.

The Honk owner separately reported combined normal/security, GCC/Clang
sanitizer/portable and normal/frozen check/package validation, unchanged locks,
and the same 127-export/15-required-file checks. This final validation includes
the SIGPIPE correction, whose native source stayed byte-identical to `ce7995d`.
It is distinct from the original isolated acceptance above.

The public [final Honk vendor manifest](https://github.com/carabistouflette/honk/blob/b8bf23641596fdc7abb6b6959ac660063cafa586/vendor/manifest.json)
records the nine canonical and two wrapper source/license files. Its SHA-256 is
`232a0196e6241496e912756012670c9e3325ce8bf39ec8229113a9703f565df0`.
Existing release tags remain unchanged. This receipt changes no source, vendor
pin, release artifact or historical validation record.
