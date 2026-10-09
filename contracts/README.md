# Canonical contract authority

The release and canonical authority is the `JCSchoeman96/ticketing-contracts` repository.
This implementation repository keeps only `authority.json`, an implementation-consumption
pin to the reviewed CANON-1 2.0.10 release at commit
`cc335793e7a542e44938883f87cc96f796a4fe32`. It is not a second canonical release.

Use `mix contract.authority` from `ticketing/` to verify a local checkout. The command checks
the Git commit, `contracts/manifest.json`, CANON-1's version, and the T0 tracer. Set
`TICKETING_CONTRACTS_PATH` when the checkout is not at the documented sibling location.
`mix contract.authority --pin-only` checks the checked-in pin fields without requiring access
to the canonical repository.
