# Ticketing authority governance

The `authority/` directory is the canonical product authority for Ticketing. The `ticketing/` directory contains the Phoenix application implementation, which is downstream of this authority.

Changes here can alter product semantics and downstream implementation authority. Treat contract work as authority engineering, not ordinary documentation editing.

The paths in this file are relative to `authority/` unless a full repository path is shown.

## Authority responsibility

This directory owns:

- CANON;
- canonical contract releases;
- paired test-gate artifacts;
- contract release provenance;
- dependency closure;
- contract manifests and hashes;
- ROADMAP execution ordering;
- active tracers;
- authority-gap correction;
- contract/planning validation tooling.

It does not own:

- Phoenix/Ash implementation architecture;
- package-version preferences;
- application source code;
- UI/component implementation;
- implementation-only database design choices;
- Plane execution state;
- coding-agent implementation decisions.

Those belong downstream unless canonical product semantics explicitly require them.

## Authority precedence

Use this precedence:

```text
authority/contracts/CANON-1 + installed canonical contracts
→ authority/planning/ROADMAP.md
→ current active tracer under authority/planning/tracers/
→ approved JIT Implementation Packet (JIP)
→ Plane execution work
→ ticketing/ implementation
```

Higher authority wins.

ROADMAP, tracers, JIPs, Plane work items, implementation code, PR comments, historical plans, reference repositories, framework conventions, and agent assumptions MUST NOT override canonical contracts.

The supporting documents under `governance/` may provide historical context, but they do not add a parallel semantic authority. If they conflict with the suite selected by CANON, the installed canonical suite controls.

## Canonical source model

The installed canonical suite in `authority/contracts/` is the semantic authority.

Use:

- `contracts/CANON-1/extracted/...`;
- `contracts/<DOC-ID>/extracted/...` selected by CANON;
- `contracts/manifest.json` for physical inventory, hashes, membership and ZIP/extract mapping.

The exact release ZIP under:

```text
contracts/<DOC-ID>/<DOC-ID>_bundle_v<VERSION>.zip
```

is the accepted release artifact.

The corresponding `extracted/` tree exists for inspection of those exact ZIP contents.

`contracts/manifest.json` records inventory and integrity. It does not independently select product semantics.

CANON selects the accepted suite.

## Candidate/source boundary

`release-src/current/...` and other editable release-source material are candidate/provenance inputs.

They are NOT installed canonical authority merely because they:

- are newer;
- contain a higher-looking version;
- are easier to edit;
- contain desired semantics;
- were generated more recently.

A candidate becomes authority only after the authority release/install process completes and the resulting exact release is selected by CANON.

Never read candidate source as though it silently supersedes the installed suite.

`authority-staging/` contains noncanonical transition candidates retained as fixtures for the current authority test gates. Its contents do not select or define installed authority; tests may use them only as candidate inputs when the paired gate explicitly requires that evidence.

## Release immutability

There is one current installed release per `doc_id`.

Accepted release bytes are immutable.

A semantic correction or change requires a successor release with a new version and new exact artifact.

NEVER replace or mutate bytes under an already accepted version while retaining the same version identity.

Do not rewrite history to make a changed contract appear to be the original accepted release.

Superseded accepted releases remain available through Git history/provenance.

## Contract version discipline

Follow the authority directory's established successor/versioning conventions.

Do not infer compatibility or semantic meaning solely from the shape of a version number.

A successor version must clearly represent a new release identity.

When a CANON member changes, produce the corresponding CANON successor and preserve exact release selection/hashes.

Do not update a contract release without reconciling every canonical artifact that depends on that exact identity.

## CANON discipline

CANON is the suite-selection authority.

When changing a CANON-selected release:

1. prepare and validate the contract successor;
2. verify dependency closure;
3. generate the required CANON successor using the authority tooling;
4. validate deterministic output;
5. install the accepted successor release(s);
6. install the matching CANON release;
7. regenerate extracted inspection copies;
8. regenerate the manifest;
9. run strict repository validation.

Do not manually edit CANON selection data in a way that bypasses the deterministic successor/generation process where the authority directory provides tooling.

CANON membership and dependency-only status must remain coherent.

## Manifest and hash discipline

Artifact identity matters.

Preserve and verify:

- release ZIP hash;
- extracted member hashes;
- file sizes where tracked;
- bundle manifest identity;
- CANON-selected release hashes;
- `contracts/manifest.json` mappings;
- provenance records;
- deterministic rebuild evidence.

A hash mismatch is not a cosmetic difference.

Do not manually "fix" a hash merely to make validation pass. Determine why bytes differ.

When generated artifacts differ unexpectedly, stop and investigate nondeterminism or source drift.

## Deterministic release construction

Successor releases must follow the authority directory's release tooling and reproducibility process.

Where the repository workflow requires two independent builds, build twice and compare the resulting:

- ZIP;
- contract artifact;
- paired test gates;
- bundle manifest;
- other deterministic generated artifacts.

Unexpected byte differences must be resolved before acceptance.

Do not bypass deterministic-build checks because the semantic diff appears correct.

## Contract bodies and test gates

Contract bodies define normative product behavior.

Paired test-gate artifacts are verification companions.

Test gates MUST:

- correspond to the correct contract/version;
- reflect contract semantics;
- stay coherent with release and manifest identity;
- provide acceptance/verification evidence without redefining the contract.

A test gate MUST NOT silently override contradictory contract text.

If contract and paired gate materially disagree, classify it as an `AUTHORITY_GAP` and repair authority explicitly.

Do not choose whichever artifact is more convenient for implementation.

## Dependency closure

Contract changes must preserve dependency closure across the installed suite.

Before accepting a successor:

- identify affected dependencies;
- identify consumers of changed semantics;
- validate required versions;
- verify CANON/dependency-only membership;
- run repository dependency/reconciliation tooling.

Do not repair a dependency contradiction by inventing an undocumented semantic bridge in planning or implementation.

If a dependent contract must change, create its proper successor.

## Technology neutrality

Canonical contracts should describe required Ticketing behavior and externally meaningful invariants, not freeze incidental implementation choices.

Do not encode moving package/framework versions such as current:

- Elixir;
- OTP;
- Ash;
- Phoenix;
- PostgreSQL;
- Tailwind;
- LiveFrames;

into canonical contracts merely because those technologies are used by the implementation.

Implementation technology changes frequently; product authority should remain valid where possible.

A technology-specific requirement belongs in canonical authority only when the technology itself is genuinely part of the required product/system contract rather than a current implementation preference.

Store Blueprint Hardening, LiveFrames, framework documentation, package behavior and implementation experiments may provide evidence or reveal gaps, but they are NOT canonical Ticketing authority.

If implementation/reference evidence reveals that a canonical requirement is impossible, contradictory or underspecified, open an `AUTHORITY_GAP`; do not silently reshape the contract to match the implementation.

## Downstream Ash-native application boundary

Canonical authority remains technology-neutral unless a technology itself is part of the product/system contract. The active `ticketing/` implementation is nevertheless governed by the repository-wide Ash-native architecture policy in the root `AGENTS.md` and the application rules in `ticketing/AGENTS.md`.

Authority, ROADMAP and tracer work MUST preserve the distinction between product semantics and downstream implementation architecture:

- derive required ownership, lifecycle, actor/tenant, authorization, transaction, concurrency, idempotency, event/outbox and persistence invariants from canonical authority;
- allow JIT/JIP to map those invariants onto Ash Domains, Ash Resources, Ash actions, policies and AshPostgres;
- treat modular derived Ash Domain/Resource ownership documentation under `ticketing/docs/domains/` as implementation architecture, not canonical semantic authority;
- do not encode a direct Repo/Ecto/raw-SQL bypass into contracts, ROADMAP or tracers merely because it appears easier to implement;
- do not weaken or reshape canonical semantics to fit a framework limitation.

If the selected Ash/AshPostgres stack cannot safely express a canonical requirement, first determine which kind of problem exists:

- missing, contradictory or insufficient canonical semantics → `AUTHORITY_GAP` and authority repair;
- clear canonical semantics but an implementation/framework limitation → downstream technical blocker/prerequisite, targeted JIT re-Grill and explicit JIP/spec decision.

A framework limitation by itself is NOT an `AUTHORITY_GAP` and MUST NOT cause canonical authority to be rewritten merely to accommodate the current implementation.

The prohibition on direct persistence bypass applies to canonical runtime application behavior in `ticketing/`. It does not prohibit authority tooling from reading/writing authority artifacts or using implementation mechanisms appropriate to deterministic contract release, validation and provenance work.

## Derived implementation documentation boundary

`ticketing/docs/` is downstream derived implementation documentation. It may describe current application architecture, Ash domains and resources, database implementation, flows, runtime and infrastructure, and historical JIP outcomes.

It MUST NOT override or silently extend CANON, canonical contracts, ROADMAP or the active tracer.

If implementation documentation exposes missing or contradictory required semantics, classify the issue through the normal authority process. A material semantic deficiency is an `AUTHORITY_GAP`; implementation documentation cannot resolve it.

Do not change authority merely to match implementation documentation without an independently justified product-authority change. Authority changes may make downstream documentation stale; refresh that documentation through normal JIT and implementation work.

## Local infrastructure governance boundary

Local infrastructure and ownership rules are downstream implementation governance. They MUST NOT create or override CANON semantics. An infrastructure or framework limitation that does not expose missing product semantics is a technical prerequisite or blocker, not automatically an `AUTHORITY_GAP`.

## Authority change PR boundary

Agent-authored changes to `authority/`, repository governance, planning/tracers, release tooling or canonical release inputs MUST also be pushed on a branch and opened as a PR before they are treated as completed or merge-ready.

Authority validation passing locally does not replace PR review. The PR MUST expose the exact diff and fresh required validation/CI evidence for independent review. Agents MUST NOT push authority/governance changes directly to `main` or self-merge unless the user explicitly authorizes that specific merge.

## Decision classes

Use these meanings consistently across authority/planning work.

### `CONTRACT_LOCKED`

Installed canonical authority determines the behavior.

Downstream planning and implementation must follow it.

### `IMPLEMENTATION_LOCKED`

Canonical authority intentionally permits alternatives and an approved downstream JIP selects one project-level implementation decision.

An `IMPLEMENTATION_LOCKED` choice MUST NOT be promoted into canonical contract semantics unless there is a separate justified product-authority reason.

### `IMPLEMENTATION_FREE`

A downstream implementation choice that cannot alter governed semantics or externally observable contract behavior.

Do not clutter canonical contracts with implementation-free details.

### `AUTHORITY_GAP`

Current authority is missing, contradictory or insufficient to determine a required material behavior safely.

Affected downstream implementation stops.

Do not invent:

- private states;
- resources;
- identifiers;
- aliases;
- transitions;
- guards;
- errors;
- events;
- payload fields;
- ownership;
- semantic bridges;
- authorization behavior;

to bypass the gap.

Resolve it explicitly through authority work.

## Authority-gap workflow

Authority work required to resolve an `AUTHORITY_GAP` does NOT require a product JIP.

Use this sequence:

```text
identify exact gap
→ identify governing/affected contracts
→ establish intended canonical semantics
→ create required successor release(s)
→ update paired gates
→ update CANON if selection changes
→ regenerate/install exact artifacts
→ verify manifest/hash/dependency closure
→ update ROADMAP/tracer only if needed
→ merge authority work
→ downstream implementation re-pins authority
→ targeted JIT re-Grill
→ revise JIP/Plane execution graph if required
→ implementation resumes
```

Keep authority PRs narrow.

Do not mix unrelated product-authority changes into a gap repair because the files are already being edited.

## ROADMAP rules

`planning/ROADMAP.md` is the active execution-order authority beneath canonical contracts. Its full repository path is `authority/planning/ROADMAP.md`.

The ROADMAP answers:

> Which contracted product path should be proved next?

It MUST NOT invent or override contract semantics.

When ROADMAP wording conflicts with canonical authority, canonical authority wins and the planning contradiction must be corrected.

Keep future horizons high-level unless their detail is already canonically established.

Do not allow a later horizon to silently expand the current tracer's scope.

## Tracer rules

The active tracer defines the contracted end-to-end path currently being proved.

A tracer may:

- identify relevant resources/actions;
- connect already-canonical semantics;
- define slice boundaries;
- identify required evidence/tests;
- document the current path through multiple contracts.

A tracer MUST NOT:

- invent missing product semantics;
- create private lifecycle states;
- fabricate identifiers;
- introduce unregistered events;
- weaken canonical invariants;
- redefine errors;
- authorize behavior contradicted by a governing contract.

If a tracer needs semantics that are not canonically established, that is an `AUTHORITY_GAP`.

A tracer may require multiple JIPs to implement.

## JIP boundary

JIPs are downstream implementation-planning artifacts.

They are not canonical contracts and should normally NOT be stored or treated here as product authority.

Only explicit user acceptance makes a JIP `APPROVED`.

Neither this authority directory nor a coding agent may self-approve a JIP.

Authority changes may make downstream JIPs stale.

When a change affects:

- CANON;
- a governing contract/version;
- tracer semantics;
- required lifecycle behavior;
- persistence invariants;
- tenancy/auth;
- concurrency/idempotency;
- money/inventory;
- error semantics;
- side effects/events;

affected JIPs must be re-evaluated through targeted JIT planning.

## Plane boundary

Plane is a downstream execution ledger.

Plane may track:

- authority-gap work;
- contract repair tasks;
- review work;
- implementation dependencies;
- discoveries and blockers.

Plane is NOT canonical product authority.

A Plane description/comment MUST NOT substitute for an accepted contract successor.

If an authority decision occurs during Plane discussion, record it in the correct canonical artifact before treating it as resolved.

The contracts workflow must not depend on optional Plane features such as custom work-item types.

## Historical and reference material

Material under areas such as:

- `planning/reference/`;
- `planning/archive/`;
- historical catalogues;
- superseded plans;
- old FPPs/JIPs;
- previous PR discussions;
- old release source;

may be used for:

- provenance;
- risks;
- test ideas;
- historical reasoning;
- migration context.

It does not become current authority merely because it contains useful detail.

Do not mechanically implement or reinstate historical sequencing.

## Planning changes versus semantic changes

A change is semantic authority work when it can alter required Ticketing behavior.

Examples include changes to:

- resource meaning;
- lifecycle;
- actions;
- required fields;
- identifiers;
- authorization;
- tenancy;
- error behavior;
- concurrency/idempotency;
- pricing/money/tax;
- inventory;
- events;
- side effects;
- externally observable behavior.

Such changes require full contract/release discipline.

Pure planning-order changes that do not alter canonical semantics may update ROADMAP/tracers without unnecessary contract successors, but still must remain coherent with installed authority.

When uncertain, treat the change as potentially semantic and verify before editing.

## Contract-writing discipline

Prefer explicit normative language.

Use `MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, and `MAY` consistently with their intended strength.

Define:

- ownership;
- inputs;
- outputs;
- invariants;
- initial state;
- transitions;
- failure behavior;
- actor/tenant constraints;
- transaction/concurrency semantics;
- replay/idempotency;
- side effects/events;
- information hiding;

where material to the contract.

Avoid examples that accidentally create normative semantics not stated by the contract.

Examples must not contradict normative text.

Do not use implementation package APIs as contract pseudocode unless the contract explicitly intends a technology-specific interface.

Ticketing code examples MUST use the canonical Ticketing namespace when application modules are shown; do not introduce legacy `V42.*` module prefixes.

## Validation

Use the authority directory's current documented validation/release commands.

Do not permanently duplicate moving tool/package versions in this file; follow the current repository requirements/CI configuration.

Before claiming authority work complete, run all applicable:

- contract tests;
- manifest verification;
- CANON generation verification;
- strict reconciliation/audit;
- candidate validation;
- dependency-set validation;
- deterministic-build comparisons;
- repository CI checks.

Do not weaken or skip a failing authority check because the intended semantic change looks correct.

If a validation tool and canonical artifact disagree unexpectedly, investigate before changing either.

## Review requirements

Authority changes require review against:

```text
base canonical suite
+ proposed semantic diff
+ successor release identity
+ paired test gates
+ dependency closure
+ CANON selection
+ manifest/hashes
+ ROADMAP/tracer impact
+ downstream staleness impact
```

Review both what changed and what must NOT have changed.

Pay special attention to accidental scope expansion and hidden downstream semantic changes.

## Mechanical exceptions

Pure typo, whitespace, formatting or comment corrections that provably cannot change semantic authority do not require successor semantic planning.

However, do not modify immutable accepted release bytes merely to fix typography.

If the typo exists inside an accepted immutable contract artifact, follow the authority successor/release policy rather than mutating that release in place.

When uncertain whether an edit affects canonical identity or meaning, use the stricter authority workflow.

## Completion and handoff

Before declaring authority work complete:

- validation passes;
- release identity is correct;
- hashes/manifests are coherent;
- CANON is coherent;
- dependency closure passes;
- paired gates match;
- ROADMAP/tracer remain coherent;
- affected downstream JIPs are identified as current or potentially stale.

After merge, downstream implementation must use the new contracts commit as its authority baseline before affected work resumes.
