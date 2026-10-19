# Deterministic UUID ordering

When UUIDs participate in canonical deterministic ordering, normalize each UUID to its 16 raw bytes and sort those bytes in unsigned lexicographic ascending order. Use the resulting byte order for hash and signature bases, apportionment tie-breaks, and other canonical UUID ordering.

Do not use UUID text, locale-sensitive collation, or another representation-dependent string ordering as the canonical order. The raw-byte comparison is required because it is the contract-defined behavior; implementations must not depend on input casing, locale, or a string collation implementation.

Useful tests include:

- canonical string input and its 16-byte input normalize to identical bytes;
- the raw-byte comparator matches the governing contract's supplied vectors;
- malformed or noncanonical inputs have deterministic behavior;
- sorting is idempotent and the canonical byte basis contains exactly 16 bytes per UUID;
- locale-sensitive collation is not used;
- any UUID memcmp vectors supplied by current SEAT-1 authority pass.

The canonical basis is the unsigned lexicographic ordering of raw 16-byte values. A string-versus-byte counterexample is not required unless current canonical authority supplies one. This is architecture guidance drawn from the archived CI-001 material. It is not a milestone before T0 unless a real T0 call site requires canonical UUID ordering.
