# Planning authority

The build order is:

```text
Current canonical contracts / CANON
→ ROADMAP.md
→ current tracer
→ implementation
```

Current contracts override planning. If a contract conflicts with this README, the roadmap, a tracer, or an implementation, use the contract and correct the planning. Do not edit a contract to preserve an older planning assumption.

[ROADMAP.md](ROADMAP.md) is the only document that answers, "What do we build next?" It identifies B0 as the minimum implementation bootstrap and T0 as the next product tracer. The T0 tracer records where the live contracts leave a product-path gap; it does not authorize implementation that violates those contracts.

Supporting documents in [architecture/](architecture/) constrain implementation only where current authority supports the constraint. They are not additional milestones.

[reference/](reference/) contains research. It is not execution order, a coding gate, or a substitute for current contracts.

[archive/](archive/) contains historical planning artifacts. Its manifests, indexes, pointers, and pack requirements are retained as history and are not active authority.

A JIP is not created for each catalogue row. Create one only for a material increment scoped by current authority and its active tracer, following the root governance gate.

Historical governance, legacy feature-pack material, TB-000, diagnostic infrastructure, and FR-1 do not create a second execution order. Check current CANON and ROADMAP before planning related work; older pack-generation requirements do not create an implementation gate.

The Phoenix application implementation lives in the monorepo's `ticketing/` directory. This location note does not authorize implementation; follow the repository authority hierarchy, current approved JIP, and Plane work item.
