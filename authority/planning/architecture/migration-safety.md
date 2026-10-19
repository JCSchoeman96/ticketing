# Migration safety

Apply migration safety when the first real product schema is introduced. That should normally happen inside T0. Do not create an empty migration-audit milestone ahead of product work.

Review migrations for:

- destructive drops, renames, and incompatible changes;
- disabling row-level security or constraints;
- tenant-owned tables without required `org_id` ownership and tenant isolation;
- raw SQL that changes security or data guarantees;
- finance or inventory changes without supporting authority;
- honest reporting when no migrations exist.

Use human-readable or machine-readable reports where they help reviewers or CI act on a real migration risk. Do not require transient feature-pack IDs as permanent migration metadata. Current contracts, migration history, and the reviewed change provide the authority for a migration.
