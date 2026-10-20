# Ticketing application agent instructions

Repository-wide authority, JIT planning, JIP approval, Plane execution, blocker/discovery capture, technology evaluation, staleness, and independent-review rules are defined by the root `../AGENTS.md`. Authority release, provenance, integrity, and validation rules are in `../authority/AGENTS.md`.

Those rules are mandatory and are not repeated here.

This file governs technical implementation inside the Phoenix/Ash/Elixir application.

Before material product/domain implementation, confirm that:

- the root governance gate is satisfied;
- the assigned Plane work item is READY and unblocked;
- it belongs to a current approved JIP;
- any required dependency/runtime/database prerequisites are already accepted.

If this file conflicts with root governance, `../AGENTS.md` controls.

## Required implementation skills

Before implementing an approved READY application work item, load `../.agents/skills/ticketing-implementation/SKILL.md`.

Load `../.agents/skills/ash-framework/SKILL.md` for Ash resources, domains, actions, policies, validations, persistence, errors, generators, or migrations. Load `../.agents/skills/phoenix-framework/SKILL.md` for Phoenix, LiveView, components, controllers, routers, plugs, endpoints, channels, or web-boundary work. Load `../.agents/skills/elixir-otp/SKILL.md` for material process, supervision, or concurrency work, not routine resource CRUD.

Before handing repository-changing implementation to PR review, load `../.agents/skills/ticketing-verification/SKILL.md`.

For documentation from installed package versions, use `mix usage_rules.docs Module.function` or search with `mix usage_rules.search_docs "search term" -p package`.

---

## Project identity

The application identity MUST remain:

- Elixir root namespace: `Ticketing`
- OTP application: `:ticketing`

Do not introduce alternative root namespaces, placeholder namespaces such as `MyApp`, or legacy `V42.*` application modules.

This is a Phoenix + LiveView + Ash Framework application written in Elixir.

## Technical freshness

Use the technical baseline selected by the current approved JIP and repository manifests.

Do not hard-code moving package patch/minor versions in this file.

When choosing APIs or implementation patterns:

- consult current official documentation for the selected dependency versions;
- prefer current supported APIs over remembered or obsolete examples;
- do not copy Ash 2.x, older Ash 3.x, Phoenix, LiveView, Ecto, Tailwind, or other patterns when the selected baseline has superseded them;
- do not silently upgrade dependencies during feature implementation;
- do not retain an obsolete API merely because older repository code uses it.

If current official guidance materially changes architecture, persistence, transactions, authorization, lifecycle, or public behavior, stop and return that decision to the JIP workflow.

## Ash Framework rules

Ash is the mandatory governed application/domain framework for canonical application state.

### Non-bypassable Ash application boundary

Canonical application/domain persistence MUST be modeled and operated through the approved Ash architecture, not through a parallel Ecto/Repo persistence layer.

For governed canonical state:

- every resource MUST be an Ash Resource and belong to an approved Ash Domain unless a user-approved JIP explicitly establishes a justified exception;
- the JIT/JIP MUST establish domain/resource ownership, public code interfaces, allowed cross-domain dependencies, actor/tenant requirements, lifecycle ownership, transaction ownership and event/outbox ownership before implementation;
- modular derived Ash Domain/Resource ownership documentation under `ticketing/docs/domains/` is derived implementation architecture and MUST NOT create or override canonical semantics;
- PostgreSQL-backed resources MUST use `AshPostgres.DataLayer` unless a user-approved JIP, after explicit JIT evaluation, selects another persistence mechanism;
- ordinary runtime reads and writes MUST pass through approved Ash actions and domain/resource code interfaces with the required actor, tenant and authorization context;
- controllers, LiveViews, jobs, service modules, provider adapters and other callers MUST use the same governed boundary rather than reaching around it;
- cross-domain behavior MUST call approved domain/action interfaces rather than couple domains through persistence access.

Direct persistence bypass is prohibited by default. Runtime/application code MUST NOT use `Ticketing.Repo`, direct `Repo` CRUD, `Ecto.Query`, `Ecto.Multi`, `insert_all`/`update_all`/`delete_all`, raw SQL, database execution helpers or equivalent mechanisms as an alternative API for canonical domain state.

Do not use `authorize?: false`, omit required actor/tenant context, bypass RLS, or duplicate Ash policy logic outside Ash merely for convenience or to make an operation succeed. Any trusted/system execution model must be explicitly designed, narrowly scoped, approved and tested.

PostgreSQL remains a defence-in-depth enforcement layer. Required foreign keys, unique/check constraints, indexes, RLS, locks, transaction primitives and other database guarantees MUST support the governed Ash/AshPostgres model; they MUST NOT become a second application persistence interface.

Low-level Repo/Ecto/SQL mechanics are allowed only for narrowly justified infrastructure work such as migrations, DDL, constraints, indexes, RLS, generated-migration correction, isolated test/fixture setup that cannot become a production shortcut, or an explicitly JIP-approved low-level mechanism needed to satisfy a locked concurrency/transaction invariant. Any approved runtime exception MUST remain behind the governed Ash action/interface boundary and preserve actor, tenant, policy, transaction, idempotency and lifecycle semantics.

If implementation appears to require bypassing Ash/AshPostgres for canonical runtime behavior, STOP affected coding. Capture a Plane blocker/discovery, identify why approved Ash mechanisms are insufficient, run targeted JIT re-Grill, and amend/approve the JIP/spec before resuming if an exception is genuinely required.

Convenience, familiarity, speculative performance concerns or shorter code are not sufficient justification for bypass.

PR review MUST scrutinize direct Repo/Ecto/raw-SQL usage and require an explicit classification/justification for every such occurrence outside ordinary Ash/AshPostgres operation.

## Local infrastructure

Local DEV and TEST use the approved shared PostgreSQL endpoints and roles defined in the root `../AGENTS.md`: DEV at `127.0.0.1:55432` with `ticketing_dev` role/database, and TEST at `127.0.0.1:55433` with `ticketing_test` role/base database. They are separate physical clusters; tests MUST preserve `MIX_TEST_PARTITION` isolation and MUST NOT connect to or mutate DEV.

Application code and tests MUST NOT lifecycle-manage workstation `dev-core`. Redis is not a current Ticketing prerequisite. After the infrastructure migration, direct local configuration MUST NOT silently fall back to legacy `postgres/postgres@localhost:5433` or legacy Redis defaults.

Infrastructure-changing implementation MUST prove DEV/TEST separation, clean PostgreSQL 18 migration, non-superuser role behavior, and absence of secret leakage. It MUST leave legacy PostgreSQL 16 and Redis volumes untouched unless separately authorized.

### Development HTTP and Tidewave ports

Ticketing DEV binds only to `127.0.0.1`. Its HTTP port comes from `TICKETING_DEV_HTTP_PORT`, with `4200` as the default. Reserve `4200` for the primary checkout and `4201–4219` for Ticketing worktrees. Do not use generic `PORT` as Ticketing's local development port contract.

Tidewave uses the same Phoenix port at `/tidewave/mcp`; the primary endpoint is `http://127.0.0.1:4200/tidewave/mcp`. For a worktree, set an available Ticketing slot, for example `TICKETING_DEV_HTTP_PORT=4201 mix phx.server`, and use `mix tidewave.proxy` when worktree-aware MCP routing is useful. Do not change another project's port allocation.

## Implementation documentation duties

Read ticket/JIP-listed `Context Docs` in addition to the authority, JIP and spec. Treat Context Docs as convenient descriptions of existing implementation, not as authority.

When implementation state changes, update only documents listed by the approved `Documentation Impact`. Create or update domain overviews, resource dossiers, platform documents, flows and navigation only when they are affected by the implemented work.

Never create speculative dossiers for unimplemented resources, duplicate large contract bodies, promote implementation choices into product authority, rewrite unrelated documents, or use documentation to justify behavior that authority or the JIP contradicts.

Where relevant, describe the actual merged implementation, including database enforcement, transaction boundaries, concurrency/version fencing, tenancy/RLS, events/outbox/jobs and interfaces.

Handoffs may be drafted during implementation. Verify their final state against the merged implementation SHA before closing the JIP.

## Application PR handoff

Every agent-authored change under `ticketing/` or to application/runtime configuration MUST be pushed and exposed through a GitHub PR before the coding agent claims completion.

The handoff MUST include the PR number/URL, final head SHA, exact changed files, verification evidence and any remaining warnings/blockers. Local verification alone does not complete the ticket.

The coding agent MUST leave the PR open for independent exact-diff review and required CI. Do not self-merge unless the user explicitly authorizes that specific merge.

### Domain behavior

Prefer:

- Ash domains;
- resources;
- actions;
- code interfaces;
- policies;
- validations;
- changes;
- preparations;
- calculations;
- aggregates;
- relationships;
- identities;
- notifiers and approved extensions;

for governed domain behavior.

Governed domain writes MUST flow through Ash actions unless the approved JIP explicitly requires infrastructure-level Repo/DDL mechanics.

Do not create parallel service-layer persistence that bypasses the approved Ash ownership model.

### Authorization

Do not bypass Ash authorization for externally initiated operations.

Pass the resolved actor through governed Ash boundaries where required.

System/service execution must use an explicit approved actor/context model rather than pretending to be a human user.

Do not use `authorize?: false` for ordinary external application behavior merely to make an action succeed.

Tests or infrastructure setup may bypass ordinary authorization only where that bypass is explicit, isolated, and cannot become a production shortcut.

### Tenancy

Tenant-scoped resources must preserve the canonical Ticketing tenancy model.

Pass the resolved tenant through Ash where required by the JIP/contracts.

Do not infer a tenant from untrusted request data after authorization has already begun.

Do not implement cross-tenant reads/writes through application-side filtering as a substitute for the required Ash/PostgreSQL isolation model.

Tenant relationships, identities, indexes, RLS behavior, and information-hiding semantics must remain consistent with the approved JIP and canonical authority.

### Actions and ownership

Use explicit actions that represent domain intent.

Prefer:

```text
publish_event
claim_inventory
create_checkout
activate_revision
```

over generic updates whose meaning is reconstructed outside the resource.

Do not put domain semantics in controllers, LiveViews, templates, workers, provider modules, or raw Repo calls when that behavior belongs in an Ash domain/resource/action.

### Lifecycle behavior

When authority defines a lifecycle, implement it as governed transitions rather than arbitrary field mutation.

Lifecycle implementations must preserve, where applicable:

- initial state;
- permitted transitions;
- initiator/actor rules;
- guards and preconditions;
- invalid-transition behavior;
- transaction boundary;
- optimistic/concurrency fencing;
- side effects;
- terminal states;
- transition tests.

Use AshStateMachine or another approved Ash capability when the JIP adopts it; do not introduce it independently merely because a resource has a status field.

### Atomicity and concurrency

Prefer Ash atomic operations when the contract/JIP requires atomic semantics and the selected Ash capability can express them correctly.

Do not silently weaken:

- CAS;
- optimistic locking;
- atomic increments;
- uniqueness;
- contention behavior;
- rollback semantics;
- idempotency;

because a read-then-write implementation is simpler.

If current Ash APIs cannot satisfy a locked concurrency requirement, stop and report the limitation instead of creating a weaker substitute.

### Transactions

Preserve transaction boundaries defined by the JIP.

State changes and required durable outbox/event records that must commit atomically must participate in the same database transaction.

Do not move side effects inside or outside a transaction merely for implementation convenience.

When post-commit delivery is required, persistence and delivery must remain distinct.

### Notifications, Signals and events

Ash notifications, Ash Signals, notifiers, jobs, domain events and the canonical Ticketing event/outbox model are not automatically interchangeable.

Use only the mechanism adopted by the current JIP.

A framework signal MUST NOT replace a contract-required durable event/outbox merely because Signals are available.

Conversely, do not build custom infrastructure when an approved current Ash capability correctly satisfies the required semantics.

### Ash extensions

Capabilities such as:

- Ash Signals;
- Temporal Resources;
- Ash Storage;
- AshStateMachine;
- AshOban;
- AshPaperTrail / AshArchival;
- AshAuthentication;
- Reactor;
- other Ash extensions;

must follow the root JIT capability-evaluation decision.

Do not add or upgrade an Ash extension silently from an implementation ticket.

### Ash migrations and generators

Use current supported Ash/Igniter generators where appropriate.

Generated migrations or source changes MUST still be inspected.

Never assume generated code automatically satisfies:

- Ticketing composite identities;
- tenant-first indexes;
- RLS;
- foreign-key semantics;
- checks;
- immutable fields;
- concurrency requirements;
- canonical naming;
- rollback requirements.

Review generated migrations before applying them.

## PostgreSQL and persistence

PostgreSQL is a semantic enforcement layer, not merely Ash storage.

Where required by the JIP/contracts, use database-enforced:

- primary keys;
- foreign keys;
- composite foreign keys;
- unique constraints;
- check constraints;
- indexes;
- RLS policies;
- immutable or monotonic invariants.

Do not rely only on Ash validation for invariants that must survive races or non-application database access.

Migration names must describe the capability/invariant introduced.

Do not hand-edit historical applied migrations to change production semantics; create a new migration unless the migration is unquestionably unreleased/local-only and the JIP permits replacement.

## Store Blueprint Hardening reference

`JCSchoeman96/Store_Blueprint_Hardening` is the primary reusable implementation reference for commerce-engine behavior.

For work involving:

- product/catalog concepts;
- carts;
- pricing;
- checkout;
- orders;
- payments;
- payment providers;
- webhooks;
- money;
- fulfillment;
- subscriptions;
- digital delivery;
- notifications;
- jobs/outbox;
- idempotency;
- retry/replay;
- commerce performance/scaling;

inspect the corresponding accepted Store Blueprint implementation before writing an equivalent mechanism from scratch.

Prefer reuse or adaptation of proven compatible:

- modules;
- patterns;
- test strategies;
- provider boundaries;
- domain facades;
- idempotency logic;
- transaction structures;
- worker patterns;
- money handling;
- performance safeguards.

Do not copy Store Blueprint semantics blindly.

Ticketing authority wins where the systems differ, especially around:

- multitenancy;
- actors/auth;
- resource ownership;
- identifiers;
- lifecycle;
- event ownership;
- APIs;
- inventory/ticketing semantics.

Any substantial reuse must remain understandable as Ticketing code rather than an unexplained copied subsystem.

## LiveFrames frontend reference

`JCSchoeman96/LiveFrames` is the primary reusable frontend/component reference.

Before implementing a reusable Ticketing UI primitive, section, component, design-token bridge, or component-generation mechanism, inspect current accepted LiveFrames capabilities.

Prefer supported native LiveFrames components/generation where compatible with the approved Ticketing design.

Do not duplicate an equivalent component system inside Ticketing without a reason.

Do not depend on:

- LiveFrames private references;
- vendor/source runtimes;
- unpublished internal artifacts;
- redistribution-restricted material;

unless explicitly permitted by the relevant LiveFrames boundary.

Ticketing owns application behavior and domain interactions even when presentation comes from LiveFrames.

## Web boundary

Phoenix controllers and LiveViews are application adapters, not the primary home of domain rules.

Prefer this flow:

```text
HTTP / LiveView event
→ normalize/validate boundary input
→ typed/domain input
→ Ticketing domain/Ash interface
→ result
→ render/navigation/response
```

Avoid embedding domain-state transitions, pricing logic, payment semantics, authorization meaning, or persistence rules directly in web modules.

Do not call `Repo` directly from web code for governed domain operations.

Avoid constructing complex Ash queries in templates or presentation components.

Where the JIP establishes a dedicated domain/code-interface boundary, web modules MUST use it.

## Provider boundaries and webhooks

Provider adapter modules should be narrow.

They may:

- construct provider requests;
- verify signatures;
- normalize provider responses;
- translate provider-specific data into canonical application input.

They should not independently own:

- Ticketing lifecycle transitions;
- persistence;
- authorization;
- business rules;
- arbitrary job orchestration.

Webhook controllers should do only the minimum trusted boundary work approved by the JIP, such as:

- obtain raw body/headers;
- verify authenticity;
- normalize the receipt;
- persist/enqueue through the approved domain boundary.

Do not treat browser return/cancel URLs or query parameters as payment proof.

## HTTP clients

Use the application's approved `Req` dependency for normal outbound HTTP.

Do not add alternative HTTP clients such as HTTPoison, Tesla, or direct `:httpc` use without an approved technical reason.

Provider/network code must define appropriate:

- timeouts;
- retry behavior;
- error normalization;
- telemetry;
- secret handling.

Retries must not create duplicate domain effects.

## Project commands

Run Mix commands from the Phoenix application directory:

```text
~/ticketing/ticketing
```

Use the project's existing aliases and supported commands.

Before claiming implementation complete, run:

```sh
mix precommit
mix check
mix check.types
```

`mix precommit` is the fast everyday gate. `mix check` runs the full non-Dialyzer quality, security, and application checks. `mix check.types` runs the separate Dialyzer gate.

and fix all failures caused by the work.

For focused development, prefer targeted commands such as:

```sh
mix test test/path/to/test.exs
mix test test/path/to/test.exs:LINE
mix test --failed
mix format
mix compile --warnings-as-errors
```

Read task help before using an unfamiliar Mix task:

```sh
mix help <task>
```

Avoid `mix deps.clean --all`; it is rarely the correct response to dependency/build problems.

## Elixir rules

Use idiomatic current Elixir.

Elixir lists do not support integer access syntax.

Do not write:

```elixir
items[0]
```

Use pattern matching, `Enum.at/2`, or appropriate `List` functions.

Elixir variables are immutable but may be rebound. Bind the result of expressions:

```elixir
socket =
  if condition do
    assign(socket, :value, value)
  else
    socket
  end
```

Do not expect reassignment inside an `if`, `case`, or `cond` branch to mutate an outer binding.

Avoid defining unrelated multiple modules in one file.

Do not use Access syntax on structs unless that struct explicitly implements Access.

Use APIs such as:

```elixir
changeset.field
Ecto.Changeset.get_field(changeset, :field)
```

as appropriate.

Never call `String.to_atom/1` on untrusted/user-controlled input.

Predicate function names should normally end in `?`. Reserve `is_*` names for guards/type-style predicates where idiomatic.

Prefer standard Elixir date/time APIs (`Date`, `Time`, `DateTime`, `Calendar`) before adding dependencies.

For concurrent bounded enumeration, prefer `Task.async_stream/3` with intentional concurrency and timeout settings.

Do not add dependencies to solve problems well-covered by Elixir/OTP without JIP justification.

## OTP and process rules

Use OTP supervision instead of unmanaged long-running processes.

Processes started by the application should have a deliberate supervision strategy.

Use named `Registry`, `DynamicSupervisor`, `Task.Supervisor`, etc. where appropriate rather than global ad-hoc process lookup.

Do not use process-local state as canonical business persistence.

Do not assume process affinity across database transactions, tasks, LiveViews, Oban jobs, or other execution contexts.

## Testing principles

Use TDD for material behavior as required by root governance.

Tests should prove externally meaningful behavior and locked invariants, not implementation trivia.

Test categories should include applicable:

- happy path;
- validation failures;
- forbidden actor;
- hidden/not-found behavior;
- cross-tenant isolation;
- invalid lifecycle transition;
- optimistic-lock/CAS conflict;
- idempotent replay;
- mismatched replay;
- concurrency/race;
- transaction rollback;
- outbox/event atomicity;
- migration/database constraint;
- provider failure;
- job retry/crash recovery.

For processes started in tests, prefer:

```elixir
start_supervised!/1
```

to guarantee cleanup.

Avoid `Process.sleep/1` as synchronization.

Prefer deterministic synchronization, messages, monitors, barriers, or process state acknowledgement.

For process termination assertions:

```elixir
ref = Process.monitor(pid)
assert_receive {:DOWN, ^ref, :process, ^pid, :normal}
```

Use `_ = :sys.get_state(pid)` when it is an appropriate deterministic way to establish that previous messages were processed.

## Phoenix conventions

Use the conventions generated/required by the selected current Phoenix baseline.

Do not reintroduce removed/deprecated Phoenix APIs.

`Phoenix.View` is obsolete for the current Phoenix architecture; do not add it.

Be mindful that router `scope` may apply a module alias.

Example:

```elixir
scope "/admin", TicketingWeb.Admin do
  pipe_through :browser

  live "/users", UserLive, :index
end
```

which resolves to `TicketingWeb.Admin.UserLive`.

Do not create redundant route aliases.

## Layouts and forms

Follow the selected Phoenix project's generated layout conventions.

For the current application architecture, LiveViews should render through the application layout component and pass required assigns such as flash/current scope when the selected Phoenix baseline expects them.

Use `Phoenix.Component.to_form/2` and `<.form>` for forms.

Use the project's imported `<.input>` component where appropriate.

Add stable, unique DOM IDs to important interactive elements such as:

- forms;
- submit buttons;
- dialogs;
- list containers;
- hooks;
- controls used by tests.

Do not test fragile generated HTML when a stable semantic element ID can be tested instead.

## HEEx rules

Use HEEx (`~H` and `.html.heex`), not legacy EEx template syntax.

Use `{...}` interpolation for attributes and simple values.

Use `<%= ... %>` for block constructs in tag bodies.

Use:

```heex
<%= for item <- @items do %>
  ...
<% end %>
```

rather than `<% Enum.each ... %>` for emitted template content.

Use HEEx comments:

```heex
<%!-- comment --%>
```

When displaying literal braces in code examples, use the appropriate `phx-no-curly-interpolation` boundary.

For multiple/conditional classes, use list syntax:

```heex
class={[
  "base classes",
  @active? && "active classes",
  if(@error?, do: "error classes", else: "normal classes")
]}
```

Do not construct invalid comma-separated class expressions outside a list.

## LiveView rules

Prefer LiveView for server-driven interactive UI where it matches the product requirement.

Name LiveViews with the `Live` suffix under `TicketingWeb`.

Use current navigation APIs such as `<.link navigate={...}>`, `<.link patch={...}>`, `push_navigate/2`, and `push_patch/2` rather than deprecated navigation APIs.

Use LiveComponents only when component lifecycle/state isolation is genuinely useful; do not introduce them reflexively.

### Streams

Use LiveView streams for dynamic or potentially large collections where incremental updates and memory behavior benefit from streams.

Do not force streams for every tiny immutable list.

When using streams:

- give the parent a stable DOM ID;
- set `phx-update="stream"`;
- consume `@streams.<name>`;
- use the generated stream item ID for each child.

Example:

```heex
<div id="messages" phx-update="stream">
  <div :for={{id, message} <- @streams.messages} id={id}>
    {message.text}
  </div>
</div>
```

Streams are not ordinary enumerable assigns.

To refilter or refresh, reload source data and reset the stream.

Track counts/empty-state information separately when required.

Do not use deprecated `phx-update="append"` or `phx-update="prepend"` collection behavior.

## LiveView JavaScript interop

Prefer server-driven LiveView behavior when possible.

For client-side behavior that genuinely needs JS:

- use supported LiveView hooks;
- give every hook element a unique DOM ID;
- if a hook owns/manipulates its DOM subtree, use the appropriate `phx-update="ignore"` boundary.

Use colocated hooks when supported by the selected LiveView baseline and appropriate to component-local behavior.

Use external hooks in `assets/js/` for reusable/global hooks.

Do not add arbitrary inline raw `<script>` elements to HEEx.

When using `push_event/3`, return or rebind the updated socket.

## LiveView tests

Use `Phoenix.LiveViewTest` and the currently selected HTML assertion tooling.

Prefer:

- `element/2`;
- `has_element?/2`;
- form helpers;
- stable DOM IDs;
- outcome assertions;

over raw HTML string comparisons.

Drive forms using LiveView test APIs such as `render_change` and `render_submit`.

Test what the user/application can observe rather than internal function calls.

If a selector test fails, inspect only the relevant HTML fragment where possible instead of dumping entire pages.

## Tailwind, CSS and frontend tooling

Use the Tailwind version selected by the current technical baseline.

Do not permanently encode a specific moving Tailwind major in this file.

Follow the selected Tailwind/Phoenix integration's current official import/content/source conventions.

Do not use obsolete Tailwind configuration patterns merely because an old example uses them.

Prefer:

1. approved reusable LiveFrames/native component output where applicable;
2. Ticketing/Phoenix components;
3. utility classes and small intentional custom CSS;

over adding another design-system/component dependency.

Do not add DaisyUI or another competing component framework without an explicit approved frontend decision.

Avoid `@apply` unless the selected frontend strategy explicitly approves it and there is a concrete reason.

Keep application JS and CSS within the supported Phoenix asset pipeline.

Do not reference arbitrary remote/vendor scripts directly from layouts when they can be safely bundled and governed locally.

## UI quality

Frontend work should be:

- accessible;
- responsive;
- keyboard usable;
- semantically structured;
- visually consistent;
- tested at relevant responsive boundaries;
- compatible with approved design tokens/components.

Include appropriate:

- loading states;
- disabled states;
- errors;
- empty states;
- focus states;
- validation feedback;
- progressive enhancement;
- reduced-motion/accessibility considerations.

Do not sacrifice accessibility or product semantics for visual fidelity.

## Security

Treat all external input as untrusted.

Never:

- convert arbitrary input to atoms;
- trust IDs/tenant IDs/roles from browser data without governed resolution;
- log secrets/tokens/raw sensitive payloads;
- expose provider secrets to LiveView/browser code;
- interpolate untrusted values into shell commands;
- construct unsafe filesystem paths;
- bypass authorization to make tests or demos pass.

Do not log raw request/response bodies unless explicitly approved and scrubbed.

## Observability

Use the canonical operation identifiers and observability rules from the approved JIP/contracts.

Do not introduce unbounded metric labels such as arbitrary:

- user IDs;
- event IDs;
- order IDs;
- tenant IDs;
- request bodies.

Logs/traces may include allowed identifiers where the canonical observability/privacy policy permits them.

Do not invent new telemetry naming schemes when the JIP/contracts define one.

## Application verification

Before claiming application work complete:

1. run focused tests while developing;
2. run relevant broader tests;
3. inspect generated migrations and artifacts;
4. run `mix format --check-formatted`;
5. run `mix compile --warnings-as-errors`;
6. run `mix precommit`, `mix check`, and `mix check.types`;
7. review the final diff;
8. report any skipped applicable check and the reason.

Never weaken or delete a meaningful failing test simply to make the suite green.

If a required rule cannot be met because the currently selected framework version behaves differently from this file, stop and report the conflict so the technical rule can be updated deliberately.
