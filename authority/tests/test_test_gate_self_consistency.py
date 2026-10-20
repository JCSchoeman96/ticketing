from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _json_pointer_value(document: object, pointer: str) -> object:
    value = document
    for encoded_part in pointer.lstrip("/").split("/"):
        part = encoded_part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            value = value[part]
        elif isinstance(value, list):
            value = value[int(part)]
        else:
            raise KeyError(pointer)
    return value


def _selected_test_gate_artifacts() -> list[tuple[str, Path, dict[str, object]]]:
    manifest = json.loads((ROOT / "contracts/manifest.json").read_text(encoding="utf-8"))
    artifacts: list[tuple[str, Path, dict[str, object]]] = []

    for contract in manifest["contracts"]:
        extracted_root = ROOT / contract["extracted_path"]
        for artifact in contract.get("artifacts", []):
            extracted_path = artifact.get("extracted_path")
            if not isinstance(extracted_path, str) or not extracted_path.endswith(".json"):
                continue
            path = extracted_root / extracted_path
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("artifact_kind") == "test_gates":
                artifacts.append((contract["doc_id"], path, payload))

    return artifacts


def test_selected_test_gate_self_json_pointer_assertions_match_actual_values() -> None:
    mismatches: list[str] = []

    for doc_id, path, gates in _selected_test_gate_artifacts():
        for gate in gates.get("gates", []):
            if not isinstance(gate, dict):
                continue
            gate_id = gate.get("id", "<unknown-gate>")
            for assertion in gate.get("assertions", []):
                if not isinstance(assertion, dict):
                    continue
                if assertion.get("mode") != "automated" or assertion.get("type") != "json_pointer_equals":
                    continue
                details = assertion.get("details")
                if not isinstance(details, dict) or details.get("artifact_kind") != "test_gates":
                    continue
                pointer = details.get("json_pointer")
                if not isinstance(pointer, str) or "equals" not in details:
                    continue

                try:
                    actual = _json_pointer_value(gates, pointer)
                except (KeyError, IndexError, ValueError, TypeError):
                    mismatches.append(
                        f"{doc_id} {gate_id}: {path.name} self-assertion points to missing {pointer}"
                    )
                    continue

                expected = details["equals"]
                if actual != expected:
                    mismatches.append(
                        f"{doc_id} {gate_id}: {path.name} asserts {pointer} == {expected!r}, "
                        f"but the selected test-gate artifact contains {actual!r}"
                    )

    assert not mismatches, "Canonical test-gate self-assertion mismatch:\n" + "\n".join(mismatches)
