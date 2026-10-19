#!/usr/bin/env python3
"""
ci_sec1_conformance_runner_v1.3.0.py

Purpose:
  ACTIVE conformance runner for SEC-1 "Byte-Truth" vectors.

Key upgrades in v1.3.0:
  - Reference JCS canonicalizer (subset-safe) for randomized CHALLENGE mode.
  - Batch protocol to avoid per-vector VM boot.
  - Evidence artifact v2 generation, optionally Ed25519-signed.
  - Deterministic transcript hash to prevent "ghost gates".

Design constraints:
  - Cross-language: implementation is invoked via an external command (runner_cmd).
  - runner_cmd MUST read JSON from stdin and write JSON to stdout (no logs on stdout).
  - All logs MUST go to stderr.

Protocols:
  - SEC1_CONFORMANCE_BATCH_v1
      stdin: {"protocol":"SEC1_CONFORMANCE_BATCH_v1","mode":"all|fixed|challenge","vectors":[...],"sec1":{"doc_id":"SEC-1","version":"..."}}
      stdout: {"protocol":"SEC1_CONFORMANCE_BATCH_v1","results":[...]}
"""

import argparse
import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

# --- Utilities ---------------------------------------------------------------

def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr, flush=True)

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def b64url_nopad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

def b64url_decode_nopad(s: str) -> bytes:
    pad = "=" * ((4 - (len(s) % 4)) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("ascii"))

def stable_json_dumps(obj: Any) -> str:
    # Minified + stable ordering for evidence signing / transcript hashing.
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

def load_sec1_contract(path: str) -> Tuple[Dict[str, Any], str]:
    \"\"\"Load SEC-1 contract and return (parsed_json, contract_artifact_sha256).

    IMPORTANT:
      contract_artifact_sha256 is computed over the exact artifact bytes of SEC-1_Contract_*.json,
      not a re-serialized JSON form. This makes pins stable and matches bundle.manifest hashing.
    \"\"\"
    if path.lower().endswith(".json"):
        with open(path, "rb") as f:
            raw = f.read()
        return json.loads(raw.decode("utf-8")), sha256_hex(raw)
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path, "r") as zf:
            candidates = [n for n in zf.namelist() if n.endswith(".json") and "/SEC-1_Contract_" in n]
            if not candidates:
                raise SystemExit("SEC-1 contract json not found in zip")
            raw = zf.read(candidates[0])
            return json.loads(raw.decode("utf-8")), sha256_hex(raw)
    raise SystemExit("Unsupported SEC-1 input (expected .json or .zip)")

# --- RFC8785/JCS canonicalization (subset-safe) ------------------------------

def _utf16_sort_key(s: str) -> bytes:
    # RFC8785 sorts object member names lexicographically by UTF-16 code units.
    return s.encode("utf-16-be", errors="surrogatepass")

def _json_escape_string(s: str) -> str:
    # Escape per JSON rules (RFC8259), minimal required escaping.
    out = []
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == '\\':
            out.append('\\\\')
        elif o < 0x20:
            out.append("\\u%04x" % o)
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'

def jcs_canonicalize(value: Any) -> str:
    # Subset-safe canonicalizer:
    # - Supports: null/bool/int/str/list/dict
    # - Numbers: int only (challenge generator enforces this).
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        # RFC8785: -0 must serialize as 0 (only relevant for floats; int(-0)==0 already).
        return str(value)
    if isinstance(value, str):
        return _json_escape_string(value)
    if isinstance(value, list):
        return "[" + ",".join(jcs_canonicalize(v) for v in value) + "]"
    if isinstance(value, dict):
        # Keys must be strings
        items: List[Tuple[str, Any]] = []
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError("Non-string key in object")
            items.append((k, v))
        items.sort(key=lambda kv: _utf16_sort_key(kv[0]))
        body = ",".join(_json_escape_string(k) + ":" + jcs_canonicalize(v) for k, v in items)
        return "{" + body + "}"
    raise ValueError(f"Unsupported type for JCS subset: {type(value).__name__}")

# --- Challenge vector generation --------------------------------------------

def _rng_from_seed(seed: str) -> "random.Random":
    import random
    # Derive deterministic 64-bit seed from provided seed text.
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    n = int.from_bytes(h[:8], "big")
    return random.Random(n)

def _rand_unicode(rng) -> str:
    # Produce visible unicode incl. non-ascii; avoid control chars.
    alphabet = [
        "a","b","c","x","y","z","-","_"," ",
        "Å","ä","ö","ß","é","ñ","Ж","中","✓","€","π","🚀"
    ]
    ln = rng.randint(1, 12)
    return "".join(rng.choice(alphabet) for _ in range(ln)).strip() or "x"

def _rand_scalar(rng):
    t = rng.randint(0, 4)
    if t == 0:
        return None
    if t == 1:
        return rng.choice([True, False])
    if t == 2:
        # int range constrained
        return rng.randint(-10_000_000, 10_000_000)
    if t == 3:
        return _rand_unicode(rng)
    return ""  # empty string edge

def _rand_value(rng, depth: int):
    if depth <= 0:
        return _rand_scalar(rng)
    t = rng.randint(0, 2)
    if t == 0:
        # object
        obj = {}
        for _ in range(rng.randint(0, 6)):
            k = _rand_unicode(rng)
            obj[k] = _rand_value(rng, depth-1)
        return obj
    if t == 1:
        arr = []
        for _ in range(rng.randint(0, 8)):
            arr.append(_rand_value(rng, depth-1))
        return arr
    return _rand_scalar(rng)

def generate_challenge_vectors(seed: str, count: int, max_depth: int) -> List[Dict[str, Any]]:
    rng = _rng_from_seed(seed)
    vectors = []
    for i in range(1, count + 1):
        payload = _rand_value(rng, max_depth)
        # Force top-level object to avoid trivialities
        if not isinstance(payload, dict):
            payload = {"payload": payload}
        canon = jcs_canonicalize(payload)
        canon_bytes = canon.encode("utf-8")
        vectors.append({
            "id": f"CHAL-{i:04d}",
            "kind": "challenge",
            "input_json_text": stable_json_dumps(payload),
            "expected_canonical_json": canon,
            "expected_utf8_bytes_b64url": b64url_nopad(canon_bytes),
            "expected_sha256_hex": sha256_hex(canon_bytes),
        })
    return vectors

# --- Runner invocation -------------------------------------------------------

def invoke_runner_batch(runner_cmd: str, stdin_obj: Dict[str, Any], timeout_s: int) -> Dict[str, Any]:
    stdin_bytes = (stable_json_dumps(stdin_obj) + "\n").encode("utf-8")
    proc = subprocess.run(
        runner_cmd,
        input=stdin_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        timeout=timeout_s,
        check=False,
    )
    if proc.returncode != 0:
        eprint(proc.stderr.decode("utf-8", errors="replace"))
        raise SystemExit(f"runner_cmd exited non-zero: {proc.returncode}")
    if proc.stderr:
        # Preserve stderr logs but don't fail.
        eprint(proc.stderr.decode("utf-8", errors="replace").rstrip())
    out = proc.stdout.decode("utf-8", errors="replace").strip()
    if not out:
        raise SystemExit("runner_cmd produced empty stdout")
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise SystemExit(f"runner_cmd stdout is not valid JSON: {e}")

# --- Evidence ---------------------------------------------------------------

def sign_evidence_if_possible(evidence_obj: Dict[str, Any], priv_b64: Optional[str]) -> Dict[str, Any]:
    # Evidence signature is optional but strongly recommended.
    if not priv_b64:
        evidence_obj["signature"] = {"present": False}
        return evidence_obj
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except Exception as e:
        raise SystemExit(f"cryptography Ed25519 not available: {e}")

    raw = b64url_decode_nopad(priv_b64)
    if len(raw) not in (32, 64):
        raise SystemExit("ed25519 private key must be 32 or 64 bytes (raw)")
    # cryptography expects 32-byte seed
    seed = raw[:32]
    sk = Ed25519PrivateKey.from_private_bytes(seed)

    unsigned = dict(evidence_obj)
    unsigned.pop("signature", None)
    msg = stable_json_dumps(unsigned).encode("utf-8")
    msg_hash = hashlib.sha256(msg).digest()
    sig = sk.sign(msg_hash)
    evidence_obj["signature"] = {
        "present": True,
        "scheme": "ed25519",
        "signed_over": "sha256(stable_json(evidence_without_signature))",
        "signature_b64url": b64url_nopad(sig),
        "message_hash_sha256_hex": msg_hash.hex(),
    }
    return evidence_obj

# --- Main -------------------------------------------------------------------


def verify_attestation(attestation: dict, signed_payload: dict) -> dict:
    """Verify the service-provided attestation signature.
    Expects:
      attestation.public_key_b64 (ed25519 public key, base64url or base64)
      attestation.signature_b64url (signature over sha256(stable_json(signed_payload)))
    Returns dict with {ok: bool, error?: str}
    """
    try:
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError
    except Exception as e:
        return {"ok": False, "error": f"PyNaCl unavailable: {e}"}

    if not isinstance(attestation, dict):
        return {"ok": False, "error": "attestation is not an object"}

    pub = attestation.get("public_key_b64")
    sig = attestation.get("signature_b64url")
    if not pub or not sig:
        return {"ok": False, "error": "missing public_key_b64 or signature_b64url"}

    # Accept base64url (nopad) or standard base64
    def _b64_any(s: str) -> bytes:
        s = s.strip()
        # base64url
        try:
            return b64url_decode_nopad(s)
        except Exception:
            pass
        # base64
        import base64
        pad = "=" * ((4 - (len(s) % 4)) % 4)
        return base64.b64decode(s + pad)

    try:
        pub_bytes = _b64_any(pub)
        sig_bytes = _b64_any(sig)
    except Exception as e:
        return {"ok": False, "error": f"base64 decode failed: {e}"}

    # Signed message is sha256 of stable json (not the raw json string)
    msg_hash = bytes.fromhex(sha256_hex(stable_json_dumps(signed_payload)))

    try:
        VerifyKey(pub_bytes).verify(msg_hash, sig_bytes)
    except BadSignatureError:
        return {"ok": False, "error": "bad signature"}
    except Exception as e:
        return {"ok": False, "error": f"verify failed: {e}"}

    return {"ok": True}
def extract_fixed_vectors(sec1: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Supports SEC-1 v3.3.x structure used in this suite.
    vectors: List[Dict[str, Any]] = []
    try:
        cj = sec1["crypto_primitives"]["canonical_json"]
        for v in cj.get("conformance_vectors", []):
            vectors.append({
                "id": v["id"],
                "kind": "fixed_jcs",
                "input_json_text": v["input_json_text"],
                "expected_canonical_json": v["expected_canonical_json"],
                "expected_utf8_bytes_b64url": v["expected_utf8_bytes_b64url"],
                "expected_sha256_hex": v["expected_sha256_hex"],
            })
    except KeyError:
        pass
    # Signature vectors are passed through as-is (implementation must handle)
    try:
        sig = sec1["crypto_primitives"]["asymmetric_signing"]
        for v in sig.get("conformance_vectors", []):
            vectors.append({
                "id": v["id"],
                "kind": "fixed_ed25519",
                "vector": v,
            })
    except KeyError:
        pass
    return vectors

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sec1", required=True, help="Path to SEC-1 contract json or JSON_ONLY bundle zip.")
    ap.add_argument("--runner-cmd", required=True, help="Shell command to invoke implementation conformance runner.")
    ap.add_argument("--mode", choices=["all", "fixed", "challenge"], default="all")
    ap.add_argument("--challenge-count", type=int, default=50)
    ap.add_argument("--challenge-seed", default=None)
    ap.add_argument("--challenge-max-depth", type=int, default=3)
    ap.add_argument("--timeout-s", type=int, default=30)
    ap.add_argument("--emit-evidence", action="store_true")
    ap.add_argument("--evidence-dir", default=".")
    ap.add_argument("--evidence-signing-private-key-b64url", default=None)
    ap.add_argument("--no-attestation", action="store_true", help="DEV ONLY: allow running without identity attestation signature.")
    ap.add_argument("--attestation-context", default="SEC1_CONFORMANCE_ATTEST_V1")
    args = ap.parse_args()

    sec1, sec1_contract_sha = load_sec1_contract(args.sec1)
    sec1_doc_id = sec1.get("doc_id", "SEC-1")
    sec1_version = sec1.get("version", "unknown")

    fixed = extract_fixed_vectors(sec1) if args.mode in ("all", "fixed") else []
    if args.challenge_seed is None:
        # Deterministic default seed: SEC-1 sha (ties evidence to contract)
        args.challenge_seed = sec1_contract_sha
    challenge = generate_challenge_vectors(args.challenge_seed, args.challenge_count, args.challenge_max_depth) if args.mode in ("all", "challenge") else []

    vectors_payload: List[Dict[str, Any]] = []
    vectors_payload.extend(fixed)
    vectors_payload.extend(challenge)

    # Transcript hash (prevents tampering with which vectors were tested)
    transcript_obj = {
        "sec1_contract_sha256": sec1_contract_sha,
        "mode": args.mode,
        "fixed_count": len([v for v in vectors_payload if v.get("kind","").startswith("fixed")]),
        "challenge_seed": args.challenge_seed if args.mode in ("all", "challenge") else None,
        "challenge_count": len([v for v in vectors_payload if v.get("kind")=="challenge"]),
        "vector_ids": [v["id"] for v in vectors_payload],
    }
    transcript_sha = sha256_hex(stable_json_dumps(transcript_obj).encode("utf-8"))

    runner_sha256 = sha256_hex(open(__file__, "rb").read())
    # Phase 7: identity attestation challenge (nonce proves "right hand" executed the tests)
    challenge_nonce_b64url = b64url_nopad(os.urandom(32))
    attestation_context = args.attestation_context
    stdin_obj = {
        "protocol": "SEC1_CONFORMANCE_BATCH_v1",
        "mode": args.mode,
        "sec1": {"doc_id": sec1_doc_id, "version": sec1_version, "contract_sha256": sec1_contract_sha},
        "transcript_sha256": transcript_sha,
        "vectors": vectors_payload,
        "attestation_challenge": {
            "context": attestation_context,
            "challenge_nonce_b64url": challenge_nonce_b64url,
            "sec1_contract_sha256": sec1_contract_sha,
            "runner_sha256": runner_sha256,
            "transcript_sha256": transcript_sha,
        },
    }

    started = time.time()
    out = invoke_runner_batch(args.runner_cmd, stdin_obj, timeout_s=args.timeout_s)
    finished = time.time()

    if out.get("protocol") != "SEC1_CONFORMANCE_BATCH_v1":
        raise SystemExit("runner_cmd returned unexpected protocol")

    results = out.get("results", [])
    if not isinstance(results, list) or not results:
        raise SystemExit("runner_cmd returned no results")

    # Validate each result
    failures: List[Dict[str, Any]] = []
    for r in results:
        vid = r.get("id")
        ok = r.get("ok")
        if ok is not True:
            failures.append({"id": vid, "reason": r.get("reason", "unknown")})
            continue

        # For JCS vectors, runner also checks expected values in challenge mode (computed) by comparing to contract expectations
        if r.get("kind") in ("fixed_jcs", "challenge"):
            # Compare sha256 if present
            exp_sha = None
            exp_b64 = None
            # Find expected record
            exp = next((v for v in vectors_payload if v["id"] == vid), None)
            if exp:
                exp_sha = exp.get("expected_sha256_hex")
                exp_b64 = exp.get("expected_utf8_bytes_b64url")
            if exp_sha and r.get("sha256_hex") != exp_sha:
                failures.append({"id": vid, "reason": "sha256_mismatch", "expected": exp_sha, "got": r.get("sha256_hex")})
            if exp_b64 and r.get("utf8_bytes_b64url") != exp_b64:
                failures.append({"id": vid, "reason": "bytes_b64url_mismatch"})
        # Signature vectors are left to implementation + optional self-check; we only require ok==true.

    passed = (len(failures) == 0)

    summary = {
        "sec1_contract_sha256": sec1_contract_sha,
        "transcript_sha256": transcript_sha,
        "mode": args.mode,
        "fixed_vectors": len(fixed),
        "challenge_vectors": len(challenge),
        "runner_cmd": args.runner_cmd,
        "result": "pass" if passed else "fail",
        "duration_ms": int((finished - started) * 1000),
        "failures": failures,
    }

    # Phase 7: Verify identity attestation signature binds to the transcript and result summary
    signed_payload = {
        "context": attestation_context,
        "challenge_nonce_b64url": challenge_nonce_b64url,
        "sec1_contract_sha256": sec1_contract_sha,
        "runner_sha256": runner_sha256,
        "transcript_sha256": transcript_sha,
        "result": summary["result"],
        "duration_ms": summary["duration_ms"],
        "mode": args.mode,
        "fixed_vectors": len(fixed),
        "challenge_vectors": (len(vectors_payload) - len(fixed)) if args.mode in ("all", "challenge") else 0,
    }
    attestation = out.get("attestation")
    if attestation is None and not args.no_attestation:
        raise SystemExit("runner_cmd did not return attestation (Phase 7 required). Use --no-attestation for dev only.")
    attestation_check = {"ok": True}
    if attestation is not None:
        attestation_check = verify_attestation(attestation, signed_payload)
        if not attestation_check.get("ok") and not args.no_attestation:
            raise SystemExit(f"attestation verification failed: {attestation_check.get('error')}")


    print(stable_json_dumps(summary))

    if args.emit_evidence:
        evidence = {
            "artifact_kind": "sec1_conformance_evidence",
            "schema_version": "sec1-conformance-evidence/3.0",
            "tool": {
                "tool_id": "SEC1-CONFORMANCE-RUNNER",
                "tool_version": "1.3.0",
                "runner_sha256": runner_sha256,
                "protocol": "SEC1_CONFORMANCE_BATCH_v1",
            },
            "sec1": {
                "doc_id": sec1_doc_id,
                "version": sec1_version,
                "contract_sha256": sec1_contract_sha,
            },
            "signed_payload": signed_payload,
            "attestation": attestation,
            "attestation_verification": attestation_check,
            "transcript": transcript_obj,
            "transcript_sha256": transcript_sha,
            "executed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_ms": summary["duration_ms"],
            "result": summary["result"],
            "failures": failures,
        }
        evidence = sign_evidence_if_possible(evidence, args.evidence_signing_private_key_b64url)
        fn = f"SEC1-CONF-EVIDENCE-{sec1_contract_sha}.json"
        out_path = os.path.join(args.evidence_dir, fn)
        with open(out_path, "wb") as f:
            f.write((stable_json_dumps(evidence) + "\n").encode("utf-8"))
        eprint(f"evidence_written: {out_path}")

if __name__ == "__main__":
    main()
