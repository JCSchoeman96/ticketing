# V42 Ticketing — A-to-Z Locked Setup, Ultimate Goal & MVP-0 Operating Blueprint

> Historical operating guide. Its MVP-0, TB-000, VS-001, and feature-registry sequencing is not the current execution order. Follow [the active roadmap](../planning/ROADMAP.md) and current CANON-pinned contracts. CANON-1 v2.0.5 records FR-1 as deferred and nonblocking.

**Document ID:** `V42-A2Z-SETUP-1`  
**Version:** `1.2.0`  
**Status:** Controlled operating guide / locked setup synthesis — non-authoritative over contract bundles  
**Generated at UTC:** `2026-05-19T21:05:00+00:00`  
**Project root namespace:** `Ticketing`  
**OTP app atom:** `:ticketing`  
**Development phase:** Legislative Mode → MVP-0 Foundation / Airlock Build only  

---

## 0. Purpose of this document

This document consolidates the full locked setup decided for the V42 Ticketing platform intelligence system: contracts, documentation, retrieval, Airlock, Domain Map, Atlas, slice planning, resource dossiers, code traceability, Ash/Spark reflection, Sourceror AST indexing, HexDocs, LightRAG, OVL/OVP overlays, local model usage, PETAL agent harness boundaries, MVP-0 scope, and the ultimate target operating model.

It is the **A-to-Z operational overview**, not a replacement for the actual contract bundles.

**Authority warning:** this document is an implementation guide and memory aid. It is not a contract artifact, not a CS-0 schema artifact, and not a source of new platform law. If this guide conflicts with V42, CS-0, BP-0, CANON, a contract bundle, paired gates, or bundle manifests, this guide is wrong and must be patched.

The doctrine is:

```text
Law first.
Evidence second.
Code third.
Production last.
```

The system exists to ensure that code is born from contract law, is mapped through deterministic architecture, is implemented with traceability, and is accepted only through CI evidence.

---

## 0A. Ultimate Goal / Target Operating Model

### 0A.1 Ultimate goal

The ultimate goal is to create a governed **contract-to-code intelligence and retrieval system** that can answer, with source-backed evidence:

1. What must happen?
2. Why must it happen?
3. Which contract defines it?
4. Which gates enforce it?
5. Which Domain Map row places it in the platform architecture?
6. Which Platform Atlas document explains its role?
7. Which development slice builds and tests it?
8. Which resource dossier maps it into Ash 3.x implementation?
9. Which module implements it?
10. Which Ash actions, policies, attributes, relationships, jobs, migrations, tests, and telemetry prove it?
11. Which CI gates currently pass or fail?
12. What is missing, stale, blocked, drifting, deprecated, or superseded?

At maturity, a human or AI agent should be able to ask:

```text
What must we implement for payment confirmation?
```

and receive a grounded answer that includes:

```text
PAY / ORD / LED / TEN / ERR / OBS / OBQC contracts
Domain Map action rows
Slice IDs
Resource dossiers
Ash resources
API/admin/frontend surfaces
Oban jobs
Events
Telemetry
Test gates
Current code modules
Current CI state
Open conflicts
```

### 0A.2 Mature target operating model

At maturity, the platform intelligence system supports:

- contract bundle ingestion;
- strict source manifests;
- deterministic Domain Map compilation;
- Platform Atlas maintenance;
- Development Slice Matrix maintenance;
- Resource Dossier creation and review;
- code-to-contract traceability;
- Ash/Spark reflection audits;
- Sourceror AST indexing for non-Ash code;
- HexDocs-backed library guidance;
- LightRAG-assisted discovery over approved sources;
- local model drafting for low-risk classification/documentation;
- PETAL-focused agent context packs;
- CI enforcement for contract, code, tenancy, execution, generated artifact, and retrieval drift;
- runtime evidence for critical operational paths;
- controlled vertical slice development after MVP-0 proof.

### 0A.3 Boundary warning

The ultimate goal defines the destination.  
**MVP-0 defines the next legal move.**

The ultimate goal does **not** authorize product implementation ahead of MVP-0 evidence.

Product vertical slices remain blocked until:

```text
MVP-0 Airlock passes
TB-000 evidence passes
VS-001 foundation proof passes
the active roadmap lock checklist is accepted
```

### 0A.4 Horizons

```text
Horizon 0 — Legislative Mode
  Contract law, architecture doctrine, Domain Map rules, Atlas/Slice/Dossier framework.

Horizon 1 — MVP-0 Foundation / Airlock
  Toolchain, ingestion, trace validation, Domain Map skeleton, TB-000, VS-001 proof.

Horizon 2 — Controlled Vertical Slice Development
  VS-002 onward, with contracts, dossiers, Ash resources, tests, telemetry, and CI evidence.

Horizon 3 — Mature AI-Assisted Delivery System
  Agents can scout, propose, patch, test, and produce evidence, but never bypass law or CI.
```

---

## 0B. Scope and non-goals of this guide

This guide is intentionally an **operating map**, not a source of contract law.

It may be used to:

```text
orient developers and agents
explain the approved retrieval/docs/code-traceability system
show the permitted MVP-0 build order
summarize which artifacts own which decisions
reduce repeated explanation across chats, PRs, and agent runs
```

It must not be used to:

```text
create new platform invariants
weaken V42 or downstream contracts
approve product implementation
replace contract bundles or paired gates
replace ADRs where a design decision still needs formal approval
bypass CI, Airlock, traceability, tenant parity, or gate checks
```

If a future contract, gate, ADR, or roadmap lock supersedes part of this guide, this guide must be patched. It must not be treated as frozen law.

---

## 1. Non-negotiable authority model

### 1.1 Truth hierarchy

Authority flows downward:

```text
V42 constitutional invariants
→ CS-0 / BP-0 / CANON
→ Contract bundle JSON
→ Paired test gates JSON
→ Bundle manifests
→ Strict Domain Map
→ Platform Atlas
→ Development Slice Matrix
→ Resource Dossiers
→ Current repository source at git SHA
→ Approved context packs / ADRs / runbooks
→ OVL / OVP overlays if valid
→ Code comments / @moduledoc / @doc
→ RAG / embeddings / summaries
→ AI-generated content
```

Rules:

- Contracts are truth.
- Generated docs are navigation.
- Code references prove alignment.
- CI decides acceptance.
- RAG is advisory.
- AI summaries are never authority.

If any Atlas, slice, dossier, overlay, RAG answer, generated doc, code comment, or agent output contradicts the contract bundle, the contract bundle wins.

### 1.2 V42 version authority

The current canonical V42 posture is:

```text
V42 Enterprise Ticketing Core Foundation Spec v1.3 = current constitutional authority.
V42 Enterprise Ticketing Core Foundation Spec v1.2.1 = older detailed foundation / historical reference.
```

v1.2.1 remains useful for background detail, historical decisions, and implementation context, but v1.3 supersedes it where there is conflict. No implementation may use v1.2.1 to weaken or bypass a v1.3 constitutional invariant or a downstream contract.

### 1.3 Source-truth lanes

The system uses three truth lanes:

```text
Contract truth:
  V42, CS-0, BP-0, CANON, contract bundles, gates, manifests.

External documentation truth:
  HexDocs, official library docs, version-pinned package docs.

Code truth:
  repo source at git SHA, Ash/Spark reflection, Sourceror AST index, tests, migrations, CI reports.
```

LightRAG may connect these lanes, but it may not merge them into an uncontrolled memory soup.

---

### 1.4 Conflict resolution and stale-source rule

Conflict resolution order is strict:

```text
1. Canonical contract bundles and their paired gates
2. V42 / CS-0 / BP-0 / CANON as applicable
3. Current published baseline pointer
4. Current roadmap lock
5. This A-to-Z guide
6. Generated/compiled navigation docs
7. RAG/AI summaries
```

If this guide says something that a contract bundle, paired gate, V42, CS-0, BP-0, CANON, or the active roadmap lock contradicts, this guide is stale.

Stale guide content must be patched; it must not be used as an implementation excuse.

---

## 2. Repository strategy

### 2.1 Workspace layout

Recommended local workspace:

```text
ticketing-workspace/
├── ticketing-contracts/
├── ticketing-platform/
├── ticketing-intelligence/
└── ticketing-infra/
```

### 2.2 Repo responsibilities

```text
ticketing-contracts
  Owns contract bundles, CS/BP/CANON baselines, raw contract law, and strict gate artifacts.

ticketing-intelligence
  Owns vault, Domain Map, Atlas, slices, dossiers, retrieval indexes, RAG, context packs, and governance reports.

ticketing-platform
  Owns Phoenix/Ash application source, tests, migrations, runtime code, and code traceability metadata.

ticketing-infra
  Owns deployment, CI runners, environment config, ops infrastructure, and production runtime infrastructure.
```

### 2.3 Dependency direction

```text
ticketing-contracts
  → ticketing-intelligence
  → ticketing-platform implementation support
```

The platform consumes contract references. It does not edit contract law.

---

## 3. V42 Knowledge Vault

### 3.1 Vault layout

```text
ticketing-intelligence/
├── contracts/
├── vault/
│   ├── Raw/
│   ├── Data/
│   ├── Compiled/
│   ├── Control/
│   └── Indexes/
├── external_docs/
├── code_index/
├── rag/
├── agent/
├── tools/
└── ci/
```

### 3.2 Vault layer meanings

```text
Raw
  Immutable source inputs. AI may read but never edit.

Data
  Deterministic extracted facts: manifests, registries, graph edges, claim ledger.

Compiled
  Human-facing generated docs: Contract Cards, Atlas docs, slice docs, dossier drafts.

Control
  Logs, reports, hot briefing, review queues, drift reports.

Indexes
  Exact, lexical, graph, vector, and retrieval indexes.
```

### 3.3 Raw is never edited

The Raw layer is append-only. If generated content is wrong, rebuild it from Raw and deterministic extracts. Do not patch Raw to make generated outputs pass.

---

## 4. Contract bundle ingestion and Airlock

### 4.1 Bundle-first rule

A contract enters the system as a bundle, not as a loose JSON file.

Correct:

```text
ORD-1_bundle_v3.7.0.zip
```

Expected internal shape:

```text
ORD-1_bundle_v3.7.0/
├── ORD-1.contract.json
├── ORD-1-GATE.test-gates.json
└── bundle.manifest.json
```

### 4.2 Bundle constraints

The Airlock validates:

- exactly one top-level folder;
- folder name format `<DOC_ID>_bundle_v<SEMVER>`;
- contract `doc_id` and `version` match folder;
- gates `doc_id` is `<DOC_ID>-GATE`;
- gates `contract_ref` matches contract;
- schema families are correct;
- `suite_schema` matches the CI-selected CS-0 version;
- gate IDs are unique and non-empty;
- manifest lists exactly all JSON artifacts except itself;
- manifest SHA-256 and byte counts match actual files.

### 4.3 Canonical contract locations

Recommended repository layout for contract ingestion:

```text
contracts/
├── raw_bundles/              # input ZIP bundles awaiting ingestion
├── baselines/                # immutable published baselines
├── current_baseline.json     # atomic pointer to active baseline
└── current_baseline/         # optional symlink to active baseline, if enabled
```

Rules:

```text
raw_bundles = input only
baselines = immutable published output
current_baseline.json = canonical published pointer
current_baseline symlink = convenience only, if enabled
```

Do not mutate a published baseline in place.

### 4.4 Hardened Python v2 scripts are current MVP-0 baseline

Current locked MVP-0 Airlock script baseline:

```text
ingest_bundle.py
build_domain_map_yaml.py
airlock_static_gates.py
```

They enforce:

```text
ZipSlip rejection
ZIP bomb protection
bounded streaming extraction
strict doc_id validation
manifest hash/byte checks
fsync-safe atomic writes
symlink-safe cleanup
immutable baseline publication
Domain Map parser hardening
```

### 4.5 Elixir Mix tasks are candidate Baseline v3

The Elixir Mix task rewrite is a candidate future replacement, not the current locked replacement.

Current conclusion:

```text
Python v2 hardened scripts = MVP-0 baseline.
Elixir Mix tasks = Baseline v3 candidate.
Elixir tasks must pass fixture parity before replacing Python v2.
```

Rule:

> The airlock implementation language is replaceable; the airlock guarantees are not.

### 4.6 Baseline publication policy

`current_baseline` must not be mutated in place.

The correct flow is:

```text
staging dir
→ full validation
→ immutable baseline dir
→ atomic pointer or symlink publication
```

Readers must only read the published baseline pointer.

Failed or interrupted staging builds must leave the current baseline unchanged.

---

### 4.7 Generated artifact and commit policy

The repo should distinguish **source inputs** from **generated outputs**.

Commit or review carefully:

```text
raw contract bundles
source manifests
generated lock files where explicitly required
human-authored Domain Map / Atlas / Slice / Dossier sources
ADR files
tooling scripts
CI workflow definitions
fixture corpora
```

Do not treat these as canonical source truth by default:

```text
vector indexes
LightRAG working directories
embedding caches
transient generated packs
ephemeral RAG state
local agent scratch files
temporary staging baselines
```

Generated outputs are useful evidence only when they are tied to a source manifest, baseline pointer, generated lock, CI run, or accepted report.

---

## 5. Deterministic Domain Map

### 5.1 Purpose

The Domain Map is the first strict architecture map. It converts contract law into parseable implementation placement.

```text
00_DOMAIN_MAP.md = authored source
00_DOMAIN_MAP.generated.yml/json = generated artifact
```

### 5.2 Locked rule

The Domain Map must use deterministic tables and approved YAML/JSON blocks.

It must not rely on LLM interpretation of free prose.

### 5.3 Required matrices

The Domain Map must include:

```text
Domain Registry
Resource Ownership Matrix
Action Execution Matrix
Cross-Domain Write Matrix
Event Flow Matrix
State Authority Matrix
Tenancy Matrix
Hot Path Matrix
External Boundary Matrix
Contract Coverage Matrix
Open Question Matrix
```

### 5.4 Strict parser requirements

The Domain Map parser must fail closed on:

- duplicate headers;
- malformed tables;
- row/header column mismatch;
- unknown required tables;
- missing required tables;
- free-prose normative `MUST`, `SHALL`, `MUST NOT`, `SHALL NOT` outside approved tables/blocks.

---

### 5.5 Source pointer stability policy

Stable references must prefer semantic pointers over fragile line numbers.

Preferred pointer types:

```text
json_pointer
markdown_anchor
ash_reflection_path
code_symbol_path
hexdocs_url_anchor
artifact_hash_only
```

Display-only pointer type:

```text
line_range
```

`line_range` may help humans navigate, but it must not be the only CI-enforced traceability pointer because formatting and refactors can move lines without changing meaning.

Examples:

```text
Good:
  ORD-1.contract.json#/invariants/order_snapshot
  Ticketing.Sales.Order#action:finalize_after_payment
  Ticketing.Inventory.SeatHold#attribute:org_id
  docs/platform-atlas/07_INVARIANT_GATE_TRACEABILITY.md#seat-hold-invariants

Bad as a stable CI pointer:
  lib/ticketing/sales/order.ex:L120-L160
```

---

## 6. Platform Atlas

### 6.1 Goal

The Platform Atlas answers:

```text
What is true about the platform?
```

It is the architecture map, not the delivery backlog.

### 6.2 Required Atlas documents

```text
00_DOMAIN_MAP.md
01_CONTRACT_REGISTER.md
02_AUTHORITY_MATRIX.md
03_DEPENDENCY_MATRIX.md
04_EVENT_FLOW_MATRIX.md
05_RESOURCE_OWNERSHIP_MATRIX.md
06_STATE_MACHINE_MATRIX.md
07_INVARIANT_GATE_TRACEABILITY.md
08_RISK_OBSERVABILITY_MATRIX.md
09_OPEN_CONFLICTS.md
10_DEVELOPMENT_SLICE_MATRIX.md
11_SLICE_TEST_TRACEABILITY.md
```

### 6.3 Atlas discipline

The Atlas may summarize and connect contract law. It may not invent behaviour.

Any undefined behaviour must be marked:

```text
NEW: proposed invariant
```

and sent back to contract review.

---

## 7. Development Slice Matrix

### 7.1 Correct mental model

Do not split each Atlas page into vertical slices.

Correct flow:

```text
Contracts
→ Domain Map
→ Platform Atlas
→ Development Slice Matrix
→ Resource Dossiers
→ Code
```

The Atlas answers **what is true**.  
The Slice Matrix answers **how we build and test it safely**.

### 7.2 Slice principle

A vertical slice is not “build ORD-1” or “build TKT-1”.

A vertical slice is a testable workflow that cuts through:

```text
backend
DB/migrations
Ash resources
policies
API
admin UI
buyer frontend
jobs
events
telemetry
tests
contract gates
```

### 7.3 Initial slice sequence

```text
TB-000 Governance Tracer Bullet
VS-001 Platform foundation boot
VS-002 Tenant login and org switcher
VS-003 Admin creates draft event occurrence
VS-004 Admin creates ticket type and price version
VS-005 Buyer reserves seat and receives checkout quote
VS-006 Payment confirmation and order finalization
VS-007 Ticket issuance and credential rendering
VS-008 Scanner admits ticket online
VS-009 Refund revokes ticket and posts reversal
VS-010 Payout eligibility and reconciliation gate
VS-011 Observability and incident-mode proof
VS-012 Export request and audit proof
```

---

## 8. Resource Dossiers

### 8.1 Purpose

Resource Dossiers bridge contract law into Ash 3.x implementation.

They are created when a slice is approaching implementation.

### 8.2 Required dossier sections

Each dossier must include:

```text
Purpose and boundaries
Contracts mapped
Slices mapped
V42 invariants mapped
Ash module name
Attributes
Relationships
Actions
Policies
Tenant strategy
State transitions
Events emitted/consumed
Jobs involved
Errors
Observability
Migration plan
Tests
Performance concerns
Open questions
```

### 8.3 Naming rule

Use clean domain module names:

```elixir
Ticketing.Sales.Order
Ticketing.Inventory.SeatHold
Ticketing.Finance.JournalEntry
```

Never:

```elixir
V42.Sales.Order
Ticketing.ORD.Order
Ticketing.SEAT.SeatHold
```

Module names express domain ownership. Metadata expresses contract traceability.

---

## 9. Code traceability

### 9.1 MVP-0 starting point

Use compile-safe metadata attributes first:

```elixir
@contract_refs ["ORD-1@3.7.0", "TEN-1@1.7.12"]
@slice_refs ["VS-006"]
@dossier_ref "Ticketing.Sales.Order"
```

### 9.2 Future Ash/Spark extension

Later, `Ticketing.Extensions.ContractTrace` may provide an Ash DSL extension:

```elixir
traceability do
  dossier "Ticketing.Sales.Order"
  slices ["VS-005", "VS-006"]

  contract "ORD-1" do
    min_version "3.7.0"
    role :primary
    reason "Order lifecycle and captured price snapshots."
    actions [:finalize_after_payment]
    attributes [:org_id, :status]
  end
end
```

But this is a later enhancement, not required before MVP-0 proof.

### 9.3 Version reconciliation

Contract references will decay when versions change.

Required future tool:

```text
just airlock-reconcile-refs
mix ticketing.refs.reconcile
```

Version bump policy:

```text
patch bump → may be proposed automatically
minor bump → human review required
major bump → no auto-apply; impact review required
```

---

## 10. Ash/Spark reflection and Sourceror AST indexing

### 10.1 Final decision

```text
Ash/Spark reflection = primary truth for Ash resources
Sourceror AST = secondary/general code intelligence
ExUnit/runtime checks = behaviour proof
```

### 10.2 Use Ash/Spark reflection for

```text
Ash resources
Ash domains
attributes
actions
relationships
identities
policies
multitenancy declarations
calculations
aggregates
```

### 10.3 Use Sourceror for

```text
non-Ash modules
@moduledoc
@doc
@spec
module metadata
controllers
LiveViews
Oban workers
routers
helper modules
source navigation
fallback AST facts
```

### 10.4 Behaviour proof

Reflection and AST describe structure. They do not prove behaviour.

Behaviour is proven by:

```text
ExUnit tests
Ash policy tests
API tests
LiveView tests
Oban job tests
migration checks
telemetry checks
CI gates
```

---

## 11. Retrieval architecture

### 11.1 Retrieval order

Do not use vector search first.

Use:

```text
1. Exact lookup
2. Graph lookup
3. Lexical lookup
4. Vector lookup
5. Reranker
6. LLM synthesis from a source pack
```

### 11.2 Golden rule

```text
Exact beats semantic.
Source beats summary.
Contract beats Atlas.
Gate beats interpretation.
CI beats confidence.
```

### 11.3 Query routing

```text
Contract/business rule query:
  exact contract lookup → graph → lexical → LightRAG → reranker

Code implementation query:
  Ash/Spark reflection → Sourceror AST → tests → optional LightRAG context

External library query:
  HexDocs MCP/version-pinned docs → exact/lexical → optional vector rerank

Planning query:
  Atlas → Slice Matrix → Dossier → contract source pack

Agent coding query:
  slice → dossier → contract → Ash reflection → AST → HexDocs
```

LightRAG is never the authority for exact code facts.

---

### 11.4 Retrieval answer contract

Any human-facing or agent-facing retrieval answer that influences implementation must state:

```text
source artifacts used
contract refs and versions
slice/dossier refs when applicable
whether code evidence was inspected
whether the answer is law, navigation, advisory, or draft
known uncertainty or missing evidence
recommended gates to run
```

Implementation answers must not rely on memory-only claims.

For exact code questions, the answer must prefer:

```text
current git SHA
Ash/Spark reflection
Sourceror AST facts
tests
CI reports
```

For business-law questions, the answer must prefer:

```text
V42
contract bundle JSON
paired gates
manifest/published baseline
Domain Map row
```

---

## 12. LightRAG, BGE-M3, and reranker

### 12.1 Locked usage

Use:

```text
LightRAG
BGE-M3 embeddings
BGE reranker
```

### 12.2 Canonical LightRAG may index

```text
Contract Cards
Platform Atlas pages
Development Slice docs
Resource Dossiers
HexDocs summaries
AST/code facts
CI reports
```

### 12.3 Canonical LightRAG must not index

```text
failed CI artifacts
raw chats
abandoned feature branches
expired prototypes
draft context packs
unaccepted generated docs
```

### 12.4 Canonical vs ephemeral RAG lanes

```text
Canonical RAG:
  main branch only
  latest successful airlock state
  accepted generated.lock.json
  shared / durable

Ephemeral Local RAG:
  developer-local
  current git SHA
  disposable
  never promoted to canonical graph
  subordinate to canonical baseline
```

Ephemeral RAG may help on a branch, but it cannot become truth.

---

### 12.5 Canonical RAG freshness and ingestion gate

Canonical RAG must only ingest from:

```text
main branch
latest successful Airlock run
accepted generated.lock.json
published baseline pointer
accepted Atlas/Slice/Dossier sources
accepted CI reports
```

Canonical RAG must not ingest:

```text
failed CI reports
local uncommitted files
feature branch scratch state
expired sandbox prototypes
unaccepted context packs
stale generated outputs
```

Every canonical RAG index build should record:

```text
git_sha
baseline_id
generated_lock_sha256
source_manifest_sha256
build_time
source count
excluded source count
```

Ephemeral local RAG must clearly label itself as local, disposable, and subordinate to canonical baseline authority.

---

## 13. OVL / OVP overlays

### 13.1 Role

OVL / OVP overlays are advisory semantic companions and retrieval helpers.

They may help connect meaning, lore, context, and developer guidance.

### 13.2 Status handling

Overlay status must be known:

```text
valid
invalid
missing
not_applicable
```

If invalid or missing, the harness falls back to law-only retrieval.

### 13.3 No override rule

Overlays cannot override:

```text
V42
CS-0
BP-0
CANON
contract JSON
test gates
bundle manifests
```

---

## 14. HexDocs MCP and external docs

### 14.1 Role

HexDocs MCP answers:

```text
How do we implement this correctly with the library?
```

It does not answer:

```text
What must the domain law be?
```

### 14.2 Version-pinned docs

Version-pinned docs should cover:

```text
Ash 3.x
AshPostgres
AshAuthentication
Phoenix
Phoenix LiveView
Ecto
Oban
Decimal
Sourceror
Telemetry
Rustler if needed
```

External docs are implementation guidance, not platform law.

---

## 15. Local models / Gemma role

### 15.1 Allowed uses

Local models may help with:

```text
classification
summaries
documentation drafts
@moduledoc drafts
@doc drafts
@spec suggestions
traceability insertion
retrieval intent suggestions
first-pass dossier stubs
```

### 15.2 Forbidden uses

Local models must not:

```text
make final contract interpretations
design finance/ledger behaviour
design tenancy policy
design security boundaries
approve migration safety
approve production code
edit contracts
claim implementation success
override CI
```

### 15.3 Output discipline

Local model outputs must be:

```text
schema-validated
or diff-guarded
or marked ai_suggested / human_review_required
```

---

## 16. PETAL agent harness

### 16.1 Doctrine

The PETAL agent harness must be:

```text
contract-first
source-backed
human-approved
validation-gated
small-scope by default
```

### 16.2 Scout/build flow

```text
/scout
  → classify route/risk
  → retrieve law
  → retrieve deterministic code evidence
  → produce context pack
  → human review
  → /scout_build only from approved context
  → run gates
  → produce evidence
```

The harness may not invent architecture from memory.

### 16.3 Context pack minimum

A coding context pack must include:

```text
contract refs
slice refs
dossier refs
relevant Domain Map rows
Ash reflection facts
AST facts where needed
HexDocs snippets where needed
risk classification
gates to run
known blocked areas
```

---

## 17. MVP-0 / Airlock boundary

### 17.1 MVP-0 starts with thin deterministic spine

Build order:

```text
1. minimal contract ingestion
2. minimal source_manifest
3. minimal contract_register
4. minimal Domain Map skeleton
5. minimal trace validator
6. Phoenix/Ash skeleton
7. TB-000 AirlockTrace proof
```

Not full RAG first.  
Not product features first.

### 17.2 MVP-0 may build

```text
repo skeleton
Phoenix/Ash shell
CI wiring
contract ingestion tooling
Domain Map parser
source_manifest tooling
generated.lock tooling
trace metadata validator
TB-000
first foundation proof
```

### 17.3 MVP-0 may not build

```text
checkout
payments
seat allocation
ticket issuing
refunds
payouts
scanning admission
dynamic pricing engine
real product vertical slices
```

### 17.4 MVP-0 exit criteria

MVP-0 exits only when:

```text
contract bundles validate
source_manifest exists and validates
Domain Map parser passes
generated artifact drift gate passes
trace validator passes TB-000
sandbox physics lint passes
TB-000 evidence report passes
VS-001 foundation proof passes
CI fails closed on missing contracts, stale generated outputs, missing traceability, tenant drift
```

---

### 17.5 MVP-0 anti-bloat rule

MVP-0 exists to prove the smallest deterministic governance spine, not to build the full intelligence platform.

A proposed MVP-0 tool is allowed only if it is required to prove one of:

```text
contract ingestion
baseline publication
Domain Map skeleton
trace validation
TB-000 evidence
VS-001 foundation proof
CI fail-closed behaviour
```

Defer anything else until after TB-000 and VS-001 evidence pass, including:

```text
full production LightRAG indexing
full autonomous agent build loops
complete resource dossier generation
full codebase-wide AST knowledge graph
large dashboards for the governance system itself
```

---

## 18. TB-000 Governance Tracer Bullet

### 18.1 Purpose

TB-000 proves the governance pipeline without opening product development.

It proves:

```text
Domain Map row
→ generated artifact
→ contract/reference metadata
→ code trace metadata
→ Ash/Phoenix module
→ migration / table parity
→ Oban worker boundary
→ trace validator
→ CI gate
→ evidence report
```

### 18.2 TB-000 modules

```elixir
Ticketing.System.HealthCheck
Ticketing.System.AirlockTrace
Ticketing.System.AirlockTraceWorker
```

### 18.3 What each proves

```text
HealthCheck
  Basic runtime/skeleton metadata proof.

AirlockTrace
  Tenant-aware Ash persistence, org_id, migration/table parity, Domain Map-to-code mapping.

AirlockTraceWorker
  Oban async boundary, explicit org_id, correlation_id, idempotency metadata.
```

### 18.4 TB-000 must not implement

```text
orders
payments
seats
tickets
refunds
payouts
scanner admission
ledger posting
tenant switching
dynamic pricing
```

### 18.5 Lifecycle

`AirlockTrace` is permanent diagnostic infrastructure.

It is:

```text
low-volume
non-product
diagnostic
ops-only
permanent
```

It is not:

```text
platform AuditLog
product telemetry
customer-visible reporting
high-frequency health spam
checkout/scanning/payment path dependency
```

---

### 18.6 TB-000 evidence report minimum

The TB-000 evidence report must prove at minimum:

```text
Domain Map row exists
generated Domain Map artifact includes TB-000 rows
code metadata references TB-000 / VS-001 as appropriate
HealthCheck module compiles
AirlockTrace Ash resource compiles
AirlockTrace has org_id tenant key
AirlockTrace migration/table parity passes
AirlockTraceWorker exists and runs through Oban boundary metadata
correlation_id and idempotency metadata are present
trace validator passes
tenant parity gate passes for AirlockTrace
CI report records pass/fail evidence
```

TB-000 must test stable interfaces and metadata contracts, not fragile product-shaped data structures.

---

## 19. Phoenix / Ash skeleton rule

### 19.1 Skeleton posture

```elixir
Root module: Ticketing
OTP app: :ticketing
Framework: Phoenix / PETAL / Ash 3.x
```

### 19.2 Generator discipline

Phoenix may provide:

```text
Endpoint
Router
Controllers
LiveViews
Ecto Repo foundation
Telemetry foundation
```

Phoenix contexts must not become governed domain authority.

### 19.3 Direct Repo rule

Direct `Ticketing.Repo` calls are forbidden in governed flows unless explicitly waived.

Allowed only for:

```text
migrations
health checks
maintenance scripts
approved low-level infrastructure tooling
approved performance-critical query with waiver
```

---

## 20. Execution and authority doctrine

### 20.1 Doctrine

```text
Caches and processes may accelerate truth.
They must not become truth.
```

### 20.2 Authoritative systems

```text
Postgres / Ash / RLS
provider webhook truth
immutable ledger journals
signed evidence artifacts
```

### 20.3 Advisory systems

```text
Redis
ETS
Cachex
Phoenix PubSub
GenServers
LiveView socket assigns
browser state
mobile offline state
```

### 20.4 GenServer rule

GenServers may coordinate, cache, route, partition, or throttle.

GenServers must not own:

```text
seat holds
seat allocations
order finality
ticket validity
ledger truth
refund state
payout eligibility
admission truth
```

### 20.5 PubSub rule

PubSub broadcasts IDs, versions, event names, correlation IDs, and safe status hints.

PubSub must not broadcast money truth, ledger truth, seat ownership truth, payout truth, or admission truth.

---

## 21. LiveView and Optimistic UI

### 21.1 Finality prohibition

LiveView may drive UX.

LiveView may not decide business finality.

Allowed:

```text
LiveView sends command
LiveView shows pending optimistic state
Ash/Postgres/Oban confirms or rejects
PubSub notifies UI
LiveView refetches authoritative state
```

Forbidden:

```text
LiveView handler directly finalizes order/payment/seat/ticket truth
```

### 21.2 Standard Async Result / Revert protocol

Optimistic async flows use a canonical envelope:

```elixir
%Ticketing.Realtime.AsyncResult{
  correlation_id: "...",
  operation: :seat_hold_reserve,
  contract_ref: "SEAT-1@...",
  slice_ref: "VS-005",
  entity_ref: %{type: :seat_hold, id: "..."},
  status: :confirmed | :reverted | :timed_out | :stale,
  reason_code: "INV_SEAT_CONFLICT",
  authoritative_version: "...",
  occurred_at: ...
}
```

### 21.3 Cache invalidation rule

Optimistic revert must not rely on perfect distributed invalidation.

It must rely on:

```text
versioned advisory caches
authoritative refetch
cache entries with version checks
fallback to Ash/Postgres authority when freshness cannot be proven
```

---

## 22. Tenant Schema and Ash parity

Every tenant-owned resource must declare:

```text
tenant_scope
tenant_key
tenant_strategy
rls_required
cross_tenant_allowed
```

Default for tenant-owned resources:

```text
tenant_scope = tenant_isolated
tenant_key = org_id
tenant_strategy = ash_attribute
rls_required = yes
cross_tenant_allowed = no
```

CI must verify:

```text
Ash resource declares multitenancy
tenant attribute matches Domain Map
migration/table includes tenant key
tenantless access fails closed
cross-tenant access fails closed
TEN-1/V42 refs exist
```

A missing tenant declaration is not global. It is a hard failure.

---

## 23. Sandbox and prototype lane

### 23.1 Purpose

The sandbox lane allows discovery without pretending prototype code is production.

### 23.2 Rules

Prototype code may live under:

```elixir
Ticketing.Sandbox.*
```

or branch names like:

```text
proto/*
```

### 23.3 Sandbox physics lanes

Every sandbox module must declare one lane:

```text
:modeling
:hot_path_simulation
:async_side_effect
```

### 23.4 Prototype metadata

Prototype modules must declare:

```elixir
@prototype_owner
@prototype_purpose
@prototype_created_at
@prototype_expires_on
@prototype_decision_ref
```

### 23.5 Garbage collection

Required command:

```text
mix ticketing.sandbox.gc
```

It fails if:

```text
metadata is missing
prototype is expired
production code imports sandbox code
sandbox code reaches main/release incorrectly
```

---

## 24. Reproducible Airlock toolchain

### 24.1 Required files

```text
mise.toml or .tool-versions
.python-version
pyproject.toml
uv.lock or requirements.lock
mix.lock
justfile or Makefile
.github/workflows/airlock.yml
```

### 24.2 Commands

```text
just airlock-static
just airlock-compiled
just airlock
```

Mix aliases:

```text
mix v42.audit.static
mix v42.audit.compiled
mix v42.audit
```

### 24.3 Gate cadence

```text
pre-commit:
  static only

pre-push:
  full deterministic audit

PR CI:
  static + compiled + tests + contract gates

nightly:
  graph/retrieval/index rebuilds, stale scans, retrieval evals
```

---

## 25. CI gate matrix

Required gate families:

```text
Contract gates
Vault gates
Domain Map gates
Generated artifact gates
Code traceability gates
Ash governance lint
Tenant parity gates
Toolchain gates
TB-000 evidence gates
Reference reconciliation gates
LightRAG ingestion gates
MVP-0 thin-spine gates
Sandbox/prototype gates
Airlock ingestion and baseline publication gates
```

CI must fail closed. If a required source, reference, gate, manifest, dossier, slice, tenant declaration, or generated artifact is missing, CI fails.

Gate identifiers must be stable, non-empty, unique, and grep/search-friendly. Renaming a gate is a governance change, not cosmetic cleanup.

---

## 26. What is already locked vs deferred

### 26.1 Locked now

```text
Ultimate goal / target operating model
Authority hierarchy
Repository separation
Knowledge Vault layout
Domain Map doctrine
Platform Atlas structure
Development Slice Matrix doctrine
Resource Dossier structure
Code traceability metadata
Ash/Spark vs Sourceror boundary
LightRAG + BGE-M3 + reranker role
Canonical vs ephemeral RAG lanes
OVL/OVP advisory overlay rule
HexDocs MCP role
Local model role
PETAL agent harness doctrine
MVP-0 boundary
TB-000 scope
Airlock Python v2 baseline
Elixir Mix task candidate status
Execution/authority doctrine
Tenant parity doctrine
LiveView finality prohibition
Async revert protocol
Sandbox prototype lane
CI/Airlock gate model
```

### 26.2 Deferred

```text
Full product vertical slice implementation
Full LightRAG production indexing
Full PETAL autonomous build harness
Full ContractTrace Spark DSL extension
Elixir Airlock Baseline v3 promotion
Complete resource dossiers for all resources
Complete slice-by-slice implementation
```

---

## 27. Document maintenance and change control

This A-to-Z guide must be updated when any of the following changes:

```text
canonical V42 version
current roadmap version
current TB-000 spec version
current Airlock baseline implementation
contract bundle ingestion shape
Domain Map required matrices
retrieval routing rules
agent harness authority rules
MVP-0 exit criteria
```

Patch rule:

```text
If tooling enforces a rule, this guide should mention it.
If this guide mentions a binding rule, there must be a contract, gate, checklist, or roadmap source behind it.
```

This document should never become a dumping ground for product feature ideas. Product feature behaviour belongs in contracts, slices, dossiers, or ADRs.

---

## 28. What remains blocked

Until MVP-0 and VS-001 evidence pass, these remain blocked:

```text
ORD-1 implementation
checkout
payments
seat allocation
ticket issuance
refunds
payouts
scanner admission
dynamic pricing
real product feature development
```

---

## 29. First legal build sequence

The first legal build sequence is:

```text
1. Create workspace/repos.
2. Add Python v2 Airlock scripts as MVP-0 baseline.
3. Add contract bundles to contracts/raw_bundles.
4. Run minimal contract ingestion.
5. Generate source_manifest and contract_register.
6. Create minimal 00_DOMAIN_MAP.md skeleton.
7. Generate Domain Map artifact.
8. Add trace validator.
9. Initialize Phoenix/Ash skeleton.
10. Add minimal code trace metadata.
11. Implement TB-000 HealthCheck, AirlockTrace, AirlockTraceWorker.
12. Add migrations/table parity for AirlockTrace.
13. Add Oban worker proof for AirlockTraceWorker.
14. Run static and compiled airlock gates.
15. Produce TB-000 evidence report.
16. Only then move toward VS-001 foundation proof.
```

---

## 30. Final operating sentence

The locked setup is:

> A contract-first, evidence-gated, AI-assisted development governance system for the Ticketing platform, where V42 and the contract bundles remain truth; the vault, Domain Map, Atlas, Slice Matrix, and Dossiers organize that truth; code must declare traceability; Ash/Postgres/RLS remain authoritative for domain correctness; caches/PubSub/GenServers are advisory only; TB-000 proves the entire airlock path without opening product development; and CI enforces drift prevention before real vertical slices begin.

The short doctrine remains:

```text
Law first.
Evidence second.
Code third.
Production last.
```

---

## 31. Appendix: one-page map

```text
V42 Contracts
→ Knowledge Vault
→ Deterministic Domain Map
→ Platform Atlas
→ Development Slice Matrix
→ Resource Dossiers
→ Code Traceability
→ Ash/Spark Reflection
→ Sourceror AST Index
→ HexDocs MCP
→ LightRAG + BGE-M3 + Reranker
→ Canonical/Ephemeral RAG lanes
→ OVL/OVP advisory overlays
→ Gemma/local model assistance
→ PETAL agent harness
→ CI/Airlock enforcement
→ MVP-0 proof
→ controlled vertical slices
→ production only after evidence
```

---

## 32. Appendix: critical “do not forget” rules

1. Do not use `V42.*` as a module prefix.
2. Root module namespace is `Ticketing`.
3. OTP app atom is `:ticketing`.
4. Use Ash 3.x only.
5. Do not sort UUID strings for crypto or tie-breaks.
6. Use UUIDv7 as Postgres UUID primary keys.
7. Normalize UUIDs to raw 16-byte form and sort unsigned lexicographic bytes for deterministic crypto/tie-break lists.
8. External/API/log IDs use prefixed IDs.
9. Customer-facing order refs are short separate refs with check digit.
10. AI may assist, but CI decides.
11. RAG may discover, but contracts decide.
12. Generated docs are navigation, not law.
13. No product code before MVP-0/TB-000/VS-001 evidence passes.

---

## 33. Appendix: v1.1.0 → v1.2.0 changes

```text
Added:
  Scope and non-goals section.
  Conflict resolution and stale-source rule.
  Generated artifact and commit policy.
  Source pointer stability policy.
  Retrieval answer contract.
  Canonical RAG freshness and ingestion gate.
  MVP-0 anti-bloat rule.
  TB-000 evidence report minimum.
  Stable gate ID rule.

Clarified:
  This guide remains non-authoritative over contract bundles.
  Generated outputs need source manifests, baseline pointers, locks, or CI evidence to be trusted.
  Ephemeral RAG is local and subordinate.
```

---

## 34. Appendix: current artifact status

```text
Current canonical roadmap:
  V42 Knowledge Vault, Atlas, Retrieval & MVP-0 Airlock Roadmap v1.11.0

Current TB-000 spec:
  TB-000 Governance Tracer Bullet v1.0

Current Airlock baseline:
  Python hardened scripts v2

Current Elixir Airlock status:
  v3.1 candidate / not promoted until parity tests pass

Current A-to-Z guide:
  V42-A2Z-SETUP-1 v1.2.0
```
