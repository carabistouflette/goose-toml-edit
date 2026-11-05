# Security

This experimental library edits untrusted TOML in memory. It does not read or
write files. Applications must bound input I/O and repeated calls, and handle
atomic saving after success. Parser/input caps are not a total memory or
wall-clock guarantee; see the [API limits](docs/api.md).

Report suspected vulnerabilities through
[GitHub private vulnerability reporting](https://github.com/carabistouflette/goose-toml-edit/security/advisories/new).
Avoid public reproduction details until a coordinated fix is available.
