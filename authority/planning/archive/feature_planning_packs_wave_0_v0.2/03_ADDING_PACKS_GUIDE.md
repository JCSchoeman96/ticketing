# Adding Feature Planning Packs Without Duplication

**Purpose:** This guide tells a future chat, agent, or human maintainer how to add new Feature Planning Packs to this collection without creating duplicate packs, duplicate source-row coverage, or parallel folder structures.

**Collection rule:** This folder is append-first and preserve-first. Do not regenerate the whole structure from memory. Open the existing collection, inspect the order index and all `pack.json` files, then add only the missing pack folders.

---

## 1. Non-negotiable update rules

1. **Do not create a second pack collection** if an existing collection ZIP/folder is provided.
2. **Do not duplicate an existing `pack_id`.**
3. **Do not duplicate an existing `source_row`** unless the new pack is an explicit split pack and the split is declared.
4. **Do not renumber existing folders** unless the user explicitly asks for a renumbering pass.
5. **Do not change implemented or reviewed pack contents** unless the user asks for a patch to that exact pack.
6. **Do not infer implementation authority from the CAI or slice catalogue alone.** Use them to locate governing contracts, then reference the actual contract bundles/gates where available.
7. **Do not make product packs coding-ready while MVP-0 blockers remain unresolved.** Mark them as draft/planning if they are prepared early.
8. **Do not remove numeric gaps.** Gaps of 10 are intentional so future packs can be inserted.
9. **Do not add scratch files** inside pack folders.
10. **Always update all order indexes and manifest evidence** after adding packs.

---

## 2. Folder naming rule

Each pack folder uses this format:

```text
<ORDER4>_<SOURCE_ROW_OR_CLASS_ID>_<short-kebab-slug>/
```

Examples:

```text
0000_MVP0-000_repo-airlock-scaffold/
0010_TB-000_governance-tracer-bullet/
0020_CI-001_deterministic-uuid-binary-sort/
0030_CI-002_migration-safety-baseline/
0040_TB-001_tenant-context-rls-denial/
```

Rules:

- `ORDER4` is a zero-padded numeric sort key.
- Sort by `ORDER4`, not by TB/VS/CI class.
- TB, VS, CI, PP, OPS, MVP0, FUT labels describe the type; they do not control ordering.
- Use increments of `10` by default: `0000`, `0010`, `0020`, `0030`, `0040`.
- Use intermediate numbers only for insertions, for example `0035_TB-038_cross-tenant-red-team-test/`.
- If there is no numeric gap and the user did not authorize renumbering, append the pack later and mark the ordering caveat in the changelog.

---

## 3. Required files inside every pack folder

Every pack folder MUST contain exactly these core files unless a later version changes the standard:

```text
00_FEATURE_PLAN.md
01_CODING_AGENT_PROMPT.md
02_EVIDENCE_CHECKLIST.md
pack.json
```

Optional files are allowed only when useful and stable, for example:

```text
03_REVIEW_NOTES.md
04_SOURCE_EXTRACTS.md
```

Do not place temporary research, model scratchpads, or unreviewed drafts inside a pack folder.

---

## 4. Required `pack.json` fields

Each `pack.json` must include:

```text
order
folder
pack_id
source_row
class
title
release_phase
mvp_blocker
files
next
```

Recommended conventions:

```text
pack_id = FP-<SOURCE_ROW>-<slug>
source_row = TB-001, VS-091, CI-001, etc.
class = MVP0, TB, VS, PP, CI, OPS, or FUT
mvp_blocker = yes or no
release_phase = foundation, sell_scan_reconcile_mvp, enterprise_hardening, conditional, or future
```

If a single source row is intentionally split into multiple packs, declare the split clearly in the plan and use stable suffixes:

```text
FP-VS-002A-user-registration
FP-VS-002B-login-session
FP-VS-002C-password-recovery
```

The `source_row` may remain `VS-002`, but the split must be explicit in `00_FEATURE_PLAN.md` and `pack.json` should include a `split_part` field.

---

## 5. Order index files to update

After adding or inserting packs, update all of these root files:

```text
01_ORDER_INDEX.md
01_ORDER_INDEX.csv
01_ORDER_INDEX.json
pack_manifest.json
```

The order index must reflect the full sorted sequence. It must not list packs that do not exist on disk, and every pack folder must appear in the order index.

Also update the `next` field in the affected pack(s):

- If appending after the current final pack, change the previous final pack's `next` to the new folder.
- Set the new final pack's `next` to `TBD after Wave <N> execution evidence` or similar.
- If inserting between two packs, set previous → new → next.

---

## 6. Duplicate-prevention workflow

Before creating any new pack folder:

1. Open `01_ORDER_INDEX.json`.
2. Open every existing `pack.json`.
3. Build sets of existing:
   - `order`
   - `folder`
   - `pack_id`
   - `source_row`
   - normalized title/slug
4. For each requested new pack, check whether it already exists by:
   - exact `pack_id` match;
   - exact `source_row` match;
   - same class + same source row;
   - very similar slug/title.
5. If a requested pack exists, do not recreate it. Report it as already present.
6. If a requested pack partially overlaps an existing pack, patch the existing pack only if explicitly asked.
7. If a pack is genuinely new, assign the next available numeric order.

---

## 7. How to choose the next order number

Default append rule:

```text
next_order = highest_existing_order + 10
```

Example:

```text
0030_CI-002_migration-safety-baseline/
0040_TB-001_tenant-context-rls-denial/
```

Insertion rule:

```text
Use a number between the two existing packs if a gap exists.
```

Example:

```text
0030_CI-002_migration-safety-baseline/
0035_TB-038_cross-tenant-red-team-test/
0040_TB-001_tenant-context-rls-denial/
```

Renumbering rule:

```text
Never renumber existing folders unless the user explicitly requests a full ordering normalization pass.
```

---

## 8. Pack creation workflow

For each new pack:

1. Identify the source row from the Tracer Bullets + Vertical Slices Catalogue.
2. Use CANON-1 for suite membership and pins. Use contracts/manifest.json to find active ZIP paths and hashes.
3. Check actual contract bundles/gates where available.
4. Define the pack boundary narrowly.
5. Write `00_FEATURE_PLAN.md`.
6. Write `01_CODING_AGENT_PROMPT.md`.
7. Write `02_EVIDENCE_CHECKLIST.md`.
8. Write `pack.json`.
9. Update `01_ORDER_INDEX.md`, `.csv`, and `.json`.
10. Regenerate `pack_manifest.json` with hashes and byte sizes for all collection files except itself.
11. Zip the full updated collection.
12. Return the ZIP link plus a short changelog.

---

## 9. Validation checklist before handoff

The updated collection must pass these checks:

```text
[ ] Exactly one root folder in the ZIP.
[ ] Every pack folder starts with a unique 4-digit order number.
[ ] Every pack folder has 00_FEATURE_PLAN.md.
[ ] Every pack folder has 01_CODING_AGENT_PROMPT.md.
[ ] Every pack folder has 02_EVIDENCE_CHECKLIST.md.
[ ] Every pack folder has pack.json.
[ ] Every pack.json order matches its folder prefix.
[ ] Every pack.json folder matches the actual folder name.
[ ] Every pack_id is unique.
[ ] Every source_row is unique unless an explicit split is declared.
[ ] 01_ORDER_INDEX.md, .csv, and .json contain the same pack sequence.
[ ] The `next` chain is correct.
[ ] pack_manifest.json lists all files except itself.
[ ] pack_manifest.json hashes and byte counts match actual files.
[ ] No product implementation pack is marked coding-ready ahead of MVP-0 proof.
```

---

## 10. Changelog format

Every update should report:

```text
Version changed: vX.Y → vX.Z
Packs added:
- <folder> — <title>

Packs skipped as duplicates:
- <pack_id or source_row>

Packs patched:
- <folder> — <reason>

Indexes updated:
- 01_ORDER_INDEX.md
- 01_ORDER_INDEX.csv
- 01_ORDER_INDEX.json
- pack_manifest.json

Validation:
- unique pack IDs: PASS/FAIL
- unique orders: PASS/FAIL
- manifest parity: PASS/FAIL
- next chain: PASS/FAIL
```

---

## 11. Important doctrine

This collection is not the source of platform law. It is an implementation-planning handoff layer.

Safe chain:

```text
CAI + Slice Catalogue + Contract Bundles + Gates
→ Feature Planning Pack
→ Coding-agent prompt
→ Implementation PR
→ Tests / CI / evidence
```

Unsafe chain:

```text
CAI + Slice Catalogue
→ coding agent builds directly
```
