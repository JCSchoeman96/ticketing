# SEC-1 Active Conformance Runner (v1.3.0)

This tool turns SEC-1 “Byte-Truth” vectors into an execution proof, across Elixir/JS/Rust/Python implementations.

## What it enforces
- Fixed vectors (from SEC-1):
  - JCS canonicalization vectors
  - Ed25519 signing vectors (implementation must validate)
- Challenge vectors (generated at runtime):
  - Deterministic random JSON (subset-safe: ints/strings/bools/null/arrays/objects)
  - Runner computes expected JCS bytes and sha256; implementation must match.

## Why challenge mode exists
Static vectors can be hard-coded. Challenge vectors force the implementation to compute JCS, not replay answers.

## Protocol (stdin/stdout)
Runner calls your implementation once per run:

- stdin: JSON `{ "protocol": "SEC1_CONFORMANCE_BATCH_v1", "vectors": [...] }`
- stdout: JSON `{ "protocol": "SEC1_CONFORMANCE_BATCH_v1", "results": [...] }`

**stdout MUST be JSON only. Logs must go to stderr.**

## Usage
### Fixed + Challenge + Evidence (recommended)
```bash
python3 ci_sec1_conformance_runner_v1.3.0.py \
  --sec1 ./SEC-1_bundle_v3.3.x_JSON_ONLY.zip \
  --runner-cmd "mix ticketing.sec1_conformance" \
  --mode all \
  --challenge-count 50 \
  --emit-evidence \
  --evidence-dir ./artifacts \
  --evidence-signing-private-key-b64url "$SEC1_EVIDENCE_ED25519_PRIV_B64URL"
```

### Batch performance note
Your `runner-cmd` should start the VM once and process all vectors in one run.

## Evidence artifact (v2)
File: `SEC1-CONF-EVIDENCE-{sec1_contract_sha256}.json`

Includes:
- SEC-1 contract sha256 tested
- runner sha256 and version
- transcript hash (vector ids + seed + counts)
- pass/fail + failures
- optional Ed25519 signature over `sha256(stable_json(evidence_without_signature))`


## Phase 7: Identity Attestation (Evidence v3)

This runner now emits Evidence v3 which includes a runner-provided nonce and expects the implementation to return an `attestation` object containing an Ed25519 signature over the SHA-256 of the `signed_payload` (which includes `transcript_sha256`). Use `--no-attestation` for local dev only.
