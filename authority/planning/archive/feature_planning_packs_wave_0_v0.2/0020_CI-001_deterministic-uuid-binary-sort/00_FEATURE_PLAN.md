# Feature Planning Pack: FP-CI-001 — Deterministic UUID Binary Sort Gate


> Status: Draft implementation handoff pack.  
> Phase: Legislative Mode -> MVP-0 only.  
> Root namespace: `Ticketing`.  
> OTP app atom: `:ticketing`.  
> Ash posture: Ash 3.x only.  
> Product work: BLOCKED unless explicitly allowed by this pack.  
> Authority rule: contracts and gates win over this planning pack.


## 1. Identity

| Field | Value |
|---|---|
| `feature_pack_id` | `FP-CI-001-deterministic-uuid-binary-sort` |
| `source_row_ids` | `CI-001` |
| `classification` | `CI` |
| `FR_ref` | `FR-MVP0-CI-001` — NEW: proposed planning handle until FR-1 exists |
| `release_phase` | `foundation` |
| `mvp_blocker` | `yes` |
| `blocked_by` | `FP-TB-000-governance-tracer-bullet` |
| `blocks` | pricing signatures, apportionment, hash/signature bases, UUID tie-breaks |

## 2. Goal

Implement a deterministic gate and helper surface ensuring that any UUID list used for crypto/signature bases, apportionment, or tie-break selection is normalized to raw 16-byte UUID form and sorted by unsigned lexicographic byte order ascending.

String sorting of UUIDs for those purposes is banned.

## 3. Governing sources

| Source | Role |
|---|---|
| `V42-0` | Constitutional identifier and determinism posture |
| `V42-0` | Locked platform naming and UUID sorting baseline |
| `CANON-1` | Canonical/hash authority, modernization-blocked but relevant |
| `GOV-0` | Governance interpretation |
| `LINT-0` | Static banned-pattern enforcement |
| `CS-0`, `BP-0` | Gate/document discipline |

## 4. Required rule

```text
When hashing/signing over a list of UUIDs or using UUIDs for apportionment tie-breaks:
A. normalize each UUID to raw 16-byte form;
B. sort by unsigned lexicographic byte order ascending;
C. use that byte order for hash/signature bases and tie-break selection;
D. MUST NOT sort UUID strings for crypto/tie-break logic.
```

## 5. Definitely required resources

None. This is a code utility + CI/lint/property-test pack.

## 6. Candidate modules

```elixir
Ticketing.Foundation.UUIDs
Ticketing.Foundation.UUIDSort
Ticketing.Governance.UUIDSortGate
```

Recommended final module:

```elixir
Ticketing.Foundation.UUIDs
```

Suggested functions:

```elixir
normalize_uuid16!(uuid)
sort_uuid_bytes_asc!(uuids)
canonical_uuid_list_bytes!(uuids)
```

## 7. Definitely required actions

| Action/function | Purpose |
|---|---|
| `normalize_uuid16!/1` | Convert accepted UUID representation to raw 16-byte binary. |
| `sort_uuid_bytes_asc!/1` | Sort UUIDs by raw byte order, not string order. |
| `canonical_uuid_list_bytes!/1` | Produce deterministic concatenated byte basis for hashing/signing inputs. |

## 8. Accepted inputs

NEW: proposed implementation detail.

- Native UUID string in canonical hyphenated form.
- Raw 16-byte binary.
- Ecto UUID dumped binary if available.

Reject:

- invalid strings;
- non-UUID binaries;
- `nil`;
- maps/structs unless explicitly supported later.

## 9. DB / migrations

None.

## 10. Policies

No runtime actor policies. This is governance and deterministic utility only.

## 11. Tests

Minimum tests:

- Sort fixture list where UUID string order differs from raw byte order.
- Raw 16-byte input and string input produce same normalized bytes.
- Invalid UUID input raises/returns deterministic error.
- Property test: output is sorted by raw binary comparison.
- Property test: idempotent sorting.
- Property test: byte basis length is `16 * count`.
- Regression test: no use of `Enum.sort(uuid_strings)` in helper implementation.

## 12. Lint/gate expectations

Minimum gate IDs:

```text
CI001-001: UUID helper exists
CI001-002: UUID normalization rejects invalid inputs
CI001-003: raw byte sort fixture passes
CI001-004: string-sort counterexample proves why string sort is banned
CI001-005: property test confirms sorted binary order
CI001-006: canonical byte basis is deterministic
CI001-007: governance lint detects banned string-sort pattern in marked crypto/tie-break contexts
```

## 13. Non-goals

- Do not build pricing.
- Do not build apportionment.
- Do not build signatures.
- Do not build order refs.
- Do not change DB primary-key strategy.
- Do not introduce customer-facing IDs.

## 14. Definition of done

```text
- Helper module exists and compiles.
- Tests and property tests pass.
- Counterexample fixture proves string sort is unsafe.
- CI/lint gate exists or has a deterministic placeholder with fail-closed behaviour.
- Documentation states that string sorting UUIDs is banned for crypto/tie-break logic.
- No product feature code is introduced.
```
