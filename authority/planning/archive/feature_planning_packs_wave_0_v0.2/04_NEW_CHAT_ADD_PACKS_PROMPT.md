# Reusable Prompt — Add Feature Planning Packs to Existing Collection

Use this prompt in a new chat when you want an agent to add more Feature Planning Packs without duplicating or recreating the existing structure.

---

## Prompt to paste into a new chat

You are maintaining my Ticketing project Feature Planning Pack collection.

I will upload the latest existing Feature Planning Pack ZIP. You MUST update that existing collection. Do not create a parallel layout, do not duplicate packs, and do not regenerate from memory.

Project constants:

```text
Root Elixir namespace: Ticketing
OTP app atom: :ticketing
Framework posture: Phoenix + Ash 3.x only
Development mode: Legislative Mode / MVP-0 first
```

Your task:

```text
Add Feature Planning Packs for the requested source rows only:
<PASTE REQUESTED ROWS HERE, e.g. TB-001, TB-038, TB-002>
```

Before creating anything, you MUST inspect the existing collection:

```text
01_ORDER_INDEX.md
01_ORDER_INDEX.csv
01_ORDER_INDEX.json
all existing pack.json files
pack_manifest.json
_shared/AGENT_HANDOFF_RULES.md
03_ADDING_PACKS_GUIDE.md, if present
```

Duplicate prevention rules:

```text
1. Do not create a pack if the same pack_id already exists.
2. Do not create a pack if the same source_row already exists, unless I explicitly ask for a split pack.
3. Do not create a pack with the same folder slug/title as an existing pack.
4. Do not renumber existing folders unless I explicitly ask for a renumbering pass.
5. Do not alter existing pack contents unless the requested work is specifically a patch to that pack.
```

Folder and ordering rules:

```text
- Each pack lives in its own folder.
- Folder format: <ORDER4>_<SOURCE_ROW_OR_CLASS_ID>_<short-kebab-slug>/
- Use zero-padded numeric order keys: 0000, 0010, 0020, 0030, etc.
- The numeric prefix controls chronological implementation order.
- TB/VS/CI/PP/OPS labels are descriptive only and do not control order.
- Use +10 for ordinary appends.
- Use an intermediate number only when inserting between existing packs.
- Preserve existing order numbers.
```

Every new pack folder MUST contain:

```text
00_FEATURE_PLAN.md
01_CODING_AGENT_PROMPT.md
02_EVIDENCE_CHECKLIST.md
pack.json
```

Each pack must be narrow, implementation-safe, and must include:

```text
feature_pack_id
source_row_ids
classification
FR_ref or proposed FR_ref status
governing_contracts with versions where known
primary authority vs supporting authority
candidate_resources
definitely_required_resources or explicit TBD reason
candidate_actions
definitely_required_actions or explicit TBD reason
state_groups
policies
db_constraints
idempotency_keys
audit_events
telemetry
error_codes
oban_jobs
acceptance_tests
must_have_gates
blocked_by
blocks
non_goals
release_phase
mvp_blocker
definition_of_done
```

Authority rules:

```text
- Use CANON-1 for suite membership and pins. Use contracts/manifest.json for current release paths and hashes.
- Use the Tracer Bullets + Vertical Slices Catalogue only as the planning-control catalogue.
- Actual contract bundles and gates remain source of truth.
- If something is not defined, mark it as NEW: proposed invariant — requires contract confirmation.
- Do not invent Ash resources, actions, error codes, events, DB constraints, or policies as final truth.
- If the pack is not coding-ready, clearly mark it as draft/planning and list blockers.
```

After adding packs, you MUST update:

```text
01_ORDER_INDEX.md
01_ORDER_INDEX.csv
01_ORDER_INDEX.json
pack_manifest.json
previous/new pack.json next pointers
```

Validation required before final answer:

```text
[ ] exactly one root folder in ZIP
[ ] unique folder order numbers
[ ] unique pack_id values
[ ] no duplicate source_row values unless explicitly split
[ ] every pack folder has the required files
[ ] every pack.json matches its folder
[ ] order index files match the folder sequence
[ ] next chain is coherent
[ ] pack_manifest hashes and byte counts match actual files
[ ] no product pack is marked coding-ready before MVP-0 proof
```

Final output required:

```text
1. Updated ZIP download link.
2. Short changelog.
3. Packs added.
4. Packs skipped as duplicates, if any.
5. Validation summary.
6. Remaining risks/blockers.
```

Do not paste full pack contents into chat unless I explicitly ask. Write files and provide the ZIP.
