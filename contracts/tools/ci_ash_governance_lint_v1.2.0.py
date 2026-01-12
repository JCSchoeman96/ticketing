#!/usr/bin/env python3
"""ci_ash_governance_lint

Repo scanner that enforces Ash governance lint rules defined in LINT-0 contract JSON.

Key properties:
- Deterministic: regex-based, line-oriented scanning.
- Waiver support: inline waivers for known-safe exceptions.
- Contract-aware: validates the rules file is a real LINT-0 contract under the current Contract Suite schema family.

Version: 1.2.0

Notable changes vs 1.1.0:
- Waiver format now matches LINT-0 contract: `lint: waive <RULE_ID> <short_reason>`.
- Enforces waiver limits from LINT-0 (e.g., max_per_file, requires_reason).
- Supports both `#` and `//` line comment prefixes.

IMPORTANT:
- Waivers are line-scoped: the waiver comment must be on the same line as the matched pattern.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional


# ---------------------------
# Policy / configuration
# ---------------------------

ALLOWED_SCHEMA_VERSIONS = {"contract-suite/1.0"}
ALLOWED_SEVERITIES = {"P0", "P1", "P2"}
SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}

DEFAULT_EXCLUDES = {
    ".git",
    "_build",
    "deps",
    "node_modules",
    "assets/node_modules",
    "priv/static",
    "tmp",
    "log",
    "cover",
    ".elixir_ls",
    # Avoid linting the contract suite itself when it lives under /contracts
    "contracts",
}


# ---------------------------
# Waiver parsing
# ---------------------------

# Waiver format (single-line, end-of-line is fine):
#   # lint: waive <RULE_ID> <short_reason>
#   // lint: waive <RULE_ID> <short_reason>
#
# Notes:
# - Waivers are line-scoped.
# - <short_reason> is required (non-empty) when LINT-0 says requires_reason=true.
WAIVER_RE = re.compile(
    r"(?P<prefix>\#|//)\s*lint:\s*waive\s+(?P<rule_id>[A-Z0-9_\-]+)(?:\s+(?P<reason>.+?))?\s*$"
)


def parse_waivers(
    lines: List[str],
    *,
    requires_reason: bool,
    max_per_file: int,
) -> Tuple[Dict[int, List[str]], List[str]]:
    """Return (waivers_by_line, waiver_errors)."""

    waivers_by_line: Dict[int, List[str]] = {}
    waiver_errors: List[str] = []

    total_waivers = 0

    for i, line in enumerate(lines, start=1):
        m = WAIVER_RE.search(line)
        if not m:
            continue

        rule_id = m.group("rule_id")
        reason = (m.group("reason") or "").strip()

        total_waivers += 1
        waivers_by_line.setdefault(i, []).append(rule_id)

        if requires_reason and not reason:
            waiver_errors.append(
                f"{i}: waiver for rule '{rule_id}' is missing a short_reason (required by LINT-0)"
            )

    if max_per_file >= 0 and total_waivers > max_per_file:
        waiver_errors.append(
            f"file has {total_waivers} waivers, exceeds LINT-0 max_per_file={max_per_file}"
        )

    return waivers_by_line, waiver_errors


def is_waived(waivers: Dict[int, List[str]], line_no: int, rule_id: str) -> bool:
    return rule_id in waivers.get(line_no, [])


# ---------------------------
# Rules loading / validation
# ---------------------------

@dataclass(frozen=True)
class LintRule:
    id: str
    severity: str
    pattern: re.Pattern
    message: str


def load_rules(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    validate_rules_doc(raw, path)
    return raw


def validate_rules_doc(doc: Dict[str, Any], path: Path) -> None:
    # Minimal contract-suite metadata checks (keep strict; fail fast).
    if doc.get("artifact_kind") != "contract":
        raise SystemExit(f"Rules file is not a contract (artifact_kind != 'contract'): {path}")

    if doc.get("doc_id") != "LINT-0":
        raise SystemExit(f"Rules file doc_id must be 'LINT-0': {path}")

    schema_version = doc.get("schema_version")
    if schema_version not in ALLOWED_SCHEMA_VERSIONS:
        raise SystemExit(
            f"Rules file schema_version must be one of {sorted(ALLOWED_SCHEMA_VERSIONS)}; got '{schema_version}': {path}"
        )

    status = doc.get("status")
    if status not in ("active", "deprecated", "draft", "retired"):
        raise SystemExit(f"Rules file status must be one of active/deprecated/draft/retired; got '{status}': {path}")

    suite_schema = doc.get("suite_schema")
    if not isinstance(suite_schema, str) or not suite_schema.startswith("CS-0@"):  # minimal
        raise SystemExit(f"Rules file suite_schema must start with 'CS-0@'; got '{suite_schema}': {path}")

    # Validate banned_patterns shape.
    banned = doc.get("banned_patterns")
    if not isinstance(banned, list) or not banned:
        raise SystemExit(f"Rules file must contain a non-empty 'banned_patterns' list: {path}")

    seen_ids = set()
    for idx, rule in enumerate(banned, start=1):
        if not isinstance(rule, dict):
            raise SystemExit(f"banned_patterns[{idx}] must be an object: {path}")

        rule_id = rule.get("id")
        sev = rule.get("severity")
        pat = rule.get("pattern")
        msg = rule.get("message", "")

        if not isinstance(rule_id, str) or not rule_id.strip():
            raise SystemExit(f"banned_patterns[{idx}].id must be a non-empty string: {path}")
        if rule_id in seen_ids:
            raise SystemExit(f"Duplicate banned_patterns id '{rule_id}': {path}")
        seen_ids.add(rule_id)

        if sev not in ALLOWED_SEVERITIES:
            raise SystemExit(
                f"banned_patterns[{idx}].severity must be one of {sorted(ALLOWED_SEVERITIES)}; got '{sev}': {path}"
            )

        if not isinstance(pat, str) or not pat.strip():
            raise SystemExit(f"banned_patterns[{idx}].pattern must be a non-empty string: {path}")
        try:
            re.compile(pat)
        except re.error as e:
            raise SystemExit(f"Invalid regex for banned_patterns[{idx}] id '{rule_id}': {e} ({path})")

        if msg is not None and not isinstance(msg, str):
            raise SystemExit(f"banned_patterns[{idx}].message must be a string (or omitted): {path}")


def compile_rules(doc: Dict[str, Any]) -> List[LintRule]:
    rules: List[LintRule] = []
    for rule in doc.get("banned_patterns", []):
        rules.append(
            LintRule(
                id=rule["id"],
                severity=rule["severity"],
                pattern=re.compile(rule["pattern"]),
                message=rule.get("message", ""),
            )
        )
    return rules


def waiver_policy_from_contract(doc: Dict[str, Any]) -> Tuple[bool, int]:
    """Return (requires_reason, max_per_file)."""

    waivers = doc.get("waivers") or {}
    limits = waivers.get("limits") or {}

    requires_reason = bool(limits.get("requires_reason", False))

    max_per_file = limits.get("max_per_file")
    if isinstance(max_per_file, int):
        return requires_reason, max_per_file

    # Default hard-limit (enterprise-safe): keep small to avoid waiver abuse.
    return requires_reason, 5


# ---------------------------
# Scanning
# ---------------------------

def should_exclude_dir(dir_name: str) -> bool:
    return dir_name in DEFAULT_EXCLUDES


def iter_source_files(root: Path) -> List[Path]:
    # Conservative: scan typical Elixir/Phoenix + general project files.
    exts = {
        ".ex", ".exs",
        ".heex", ".eex",
        ".md",
        ".yml", ".yaml",
        ".json",
        ".js", ".ts",
    }

    files: List[Path] = []
    for base, dirs, filenames in os.walk(root):
        # mutate dirs in-place to prune traversal
        dirs[:] = [d for d in dirs if not should_exclude_dir(d)]
        for fn in filenames:
            p = Path(base) / fn
            if p.suffix.lower() in exts:
                files.append(p)
    return files


def scan_file(path: Path, rules: List[LintRule], *, requires_reason: bool, max_per_file: int) -> Tuple[List[Dict[str, Any]], List[str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    waivers, waiver_errors = parse_waivers(lines, requires_reason=requires_reason, max_per_file=max_per_file)

    findings: List[Dict[str, Any]] = []

    for rule in rules:
        for i, line in enumerate(lines, start=1):
            if rule.pattern.search(line):
                if is_waived(waivers, i, rule.id):
                    continue
                findings.append(
                    {
                        "rule_id": rule.id,
                        "severity": rule.severity,
                        "file": str(path),
                        "line": i,
                        "snippet": line.strip(),
                        "message": rule.message,
                    }
                )

    return findings, waiver_errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Repo root to scan")
    ap.add_argument("--rules", required=True, help="Path to LINT-0 contract JSON")
    ap.add_argument(
        "--fail_on",
        default="P1",
        choices=["P0", "P1", "P2"],
        help="Fail threshold severity (inclusive)",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    rules_doc = load_rules(Path(args.rules).resolve())
    compiled = compile_rules(rules_doc)

    requires_reason, max_per_file = waiver_policy_from_contract(rules_doc)

    threshold = SEVERITY_ORDER[args.fail_on]
    all_findings: List[Dict[str, Any]] = []
    all_waiver_errors: List[Tuple[str, str]] = []  # (file, error)

    for f in iter_source_files(root):
        findings, waiver_errors = scan_file(
            f,
            compiled,
            requires_reason=requires_reason,
            max_per_file=max_per_file,
        )
        all_findings.extend(findings)
        for we in waiver_errors:
            all_waiver_errors.append((str(f), we))

    if all_waiver_errors:
        print("Waiver Policy Violations (P0):")
        for file_path, err in all_waiver_errors:
            print(f"- [P0] {file_path}: {err}")
        # Waiver policy violations are always a hard fail.
        return 1

    if not all_findings:
        print("OK: No governance lint violations found.")
        return 0

    # Sort deterministic: severity, file, line, rule_id
    all_findings.sort(key=lambda x: (SEVERITY_ORDER.get(x["severity"], 9), x["file"], x["line"], x["rule_id"]))

    print("Governance Lint Violations:")
    for f in all_findings:
        print(f"- [{f['severity']}] {f['file']}:{f['line']} {f['rule_id']} :: {f['message']}")
        print(f"    {f['snippet']}")

    worst = min(SEVERITY_ORDER.get(f["severity"], 9) for f in all_findings)
    if worst <= threshold:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
