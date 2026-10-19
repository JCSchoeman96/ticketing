/**
 * SEAT-1 Canonical UUIDv7 Sort (memcmp semantics) — v1.0.0
 * -----------------------------------------------------------------------------
 * Purpose:
 *   Produce a deterministic, byte-wise (memcmp) lexicographical ordering of UUID
 *   strings (lowercase, hex) to satisfy SEAT-1 batch signature requirements.
 *
 * Critical rules:
 *   - NO locale-sensitive collation (no Intl.Collator).
 *   - Compare raw 16-byte UUIDs with memcmp semantics.
 *   - Input UUIDs MUST be lowercase canonical (we normalize to lowercase).
 *   - UUID format supported: 8-4-4-4-12 hex with dashes.
 *
 * Returns:
 *   - sortUuidList([...]) -> new sorted array (does NOT mutate input).
 *   - sortUuidListInPlace([...]) -> sorts in place.
 *
 * Notes:
 *   - This comparator is O(16) per compare.
 *   - This code does not attempt constant-time comparison (sorting can't be).
 */

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

/** Convert a canonical UUID string to a 16-byte Uint8Array. */
export function uuidToBytes(uuid) {
  if (typeof uuid !== "string") {
    throw new TypeError("uuidToBytes: uuid must be a string");
  }

  const u = uuid.toLowerCase();

  if (!UUID_RE.test(u)) {
    throw new Error(`uuidToBytes: invalid UUID format: ${uuid}`);
  }

  // Remove dashes: 32 hex chars.
  const hex = u.replace(/-/g, "");
  const out = new Uint8Array(16);

  for (let i = 0; i < 16; i++) {
    const byteHex = hex.slice(i * 2, i * 2 + 2);
    out[i] = parseInt(byteHex, 16);
  }

  return out;
}

/**
 * Byte-wise lexicographical compare (memcmp semantics) for UUID byte arrays.
 * Returns:
 *   -1 if a < b
 *    0 if a == b
 *    1 if a > b
 */
export function compareUuidBytes(aBytes, bBytes) {
  if (!(aBytes instanceof Uint8Array) || aBytes.length !== 16) {
    throw new Error("compareUuidBytes: aBytes must be Uint8Array(16)");
  }
  if (!(bBytes instanceof Uint8Array) || bBytes.length !== 16) {
    throw new Error("compareUuidBytes: bBytes must be Uint8Array(16)");
  }

  for (let i = 0; i < 16; i++) {
    const da = aBytes[i];
    const db = bBytes[i];
    if (da < db) return -1;
    if (da > db) return 1;
  }
  return 0;
}

/** Compare two UUID strings by memcmp semantics on their raw 16-byte values. */
export function compareUuids(a, b) {
  // Normalize to lowercase before parsing.
  const aBytes = uuidToBytes(a);
  const bBytes = uuidToBytes(b);
  return compareUuidBytes(aBytes, bBytes);
}

/** Return a NEW array sorted by UUID memcmp semantics (does not mutate input). */
export function sortUuidList(uuids) {
  if (!Array.isArray(uuids)) {
    throw new TypeError("sortUuidList: uuids must be an array of strings");
  }
  // Copy -> sort in place on copy.
  const copy = uuids.slice();
  copy.sort(compareUuids);
  return copy;
}

/** Sort the array in place by UUID memcmp semantics (mutates input). */
export function sortUuidListInPlace(uuids) {
  if (!Array.isArray(uuids)) {
    throw new TypeError("sortUuidListInPlace: uuids must be an array of strings");
  }
  uuids.sort(compareUuids);
  return uuids;
}

/**
 * Optional helper: assert the list is already sorted in canonical order.
 * Useful if your backend rejects "unsorted input" even if it would verify after sorting.
 */
export function assertSortedUuidList(uuids) {
  if (!Array.isArray(uuids)) {
    throw new TypeError("assertSortedUuidList: uuids must be an array of strings");
  }
  for (let i = 1; i < uuids.length; i++) {
    if (compareUuids(uuids[i - 1], uuids[i]) > 0) {
      throw new Error("UUID list is not sorted by SEAT-1 memcmp semantics");
    }
  }
  return true;
}
