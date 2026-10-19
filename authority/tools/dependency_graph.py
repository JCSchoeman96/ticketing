"""Dependency graph helpers for canonical audit and release-set planning."""

from __future__ import annotations

from typing import Any

from .reconcile_contracts import strongly_connected_components


def candidate_dependency_graph(
    contract_records: dict[str, dict[str, Any]],
    *,
    included_doc_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Build a proposal graph from selected candidates and unique invalid candidates.

    A doc_id with multiple unselected candidates is omitted rather than chosen
    by version or path. Invalid unique candidates remain visible for release
    planning, clearly marked as invalid.
    """

    nodes: dict[str, dict[str, Any]] = {}
    omitted: list[dict[str, Any]] = []
    for doc_id, record in sorted(contract_records.items()):
        if included_doc_ids is not None and doc_id not in included_doc_ids:
            continue
        candidates = record.get("candidates", [])
        selected = record.get("selected_candidate")
        if selected is not None:
            candidate = selected
        elif len(candidates) == 1:
            candidate = candidates[0]
        elif not candidates:
            continue
        else:
            omitted.append(
                {"doc_id": doc_id, "reason": "multiple candidates without a selected proposal"}
            )
            continue
        nodes[doc_id] = {
            "doc_id": doc_id,
            "version": candidate.get("version"),
            "path": candidate.get("source_path"),
            "zip_sha256": candidate.get("zip_sha256"),
            "contract_status": record.get("status"),
            "validation_status": (candidate.get("validation") or {}).get("status"),
        }

    edges: list[dict[str, Any]] = []
    adjacency = {doc_id: set() for doc_id in nodes}
    for doc_id, node in sorted(nodes.items()):
        record = contract_records[doc_id]
        candidate = record.get("selected_candidate")
        if candidate is None:
            candidate = record["candidates"][0]
        metadata = candidate.get("contract_metadata") or {}
        dependencies = metadata.get("dependencies", [])
        if not isinstance(dependencies, list):
            continue
        for index, dependency in enumerate(dependencies):
            if not isinstance(dependency, dict):
                continue
            target = dependency.get("doc_id")
            edge = {
                "referrer_doc_id": doc_id,
                "referrer_version": node["version"],
                "dependency_index": index,
                "target_doc_id": target,
                "target_in_graph": target in nodes,
                "edge_type": dependency.get("edge_type"),
                "minimum_version": dependency.get("min_version"),
                "reason": dependency.get("reason"),
                "purpose": dependency.get("purpose"),
            }
            edges.append(edge)
            if target in nodes:
                adjacency[doc_id].add(str(target))
    return {
        "nodes": [nodes[doc_id] for doc_id in sorted(nodes)],
        "edges": sorted(
            edges,
            key=lambda edge: (
                str(edge["referrer_doc_id"]),
                int(edge["dependency_index"]),
                str(edge["target_doc_id"]),
            ),
        ),
        "adjacency": adjacency,
        "omitted": omitted,
    }


def summarize_strongly_connected_components(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach internal and boundary edges to all SCCs in a candidate graph."""

    adjacency: dict[str, set[str]] = graph["adjacency"]
    components = strongly_connected_components(adjacency)
    summaries: list[dict[str, Any]] = []
    for members in components:
        member_set = set(members)
        internal = [
            edge
            for edge in graph["edges"]
            if edge["referrer_doc_id"] in member_set
            and edge["target_doc_id"] in member_set
        ]
        outbound = [
            edge
            for edge in graph["edges"]
            if edge["referrer_doc_id"] in member_set
            and edge["target_doc_id"] not in member_set
        ]
        inbound = [
            edge
            for edge in graph["edges"]
            if edge["referrer_doc_id"] not in member_set
            and edge["target_doc_id"] in member_set
        ]
        cyclic = len(members) > 1 or any(
            edge["referrer_doc_id"] == edge["target_doc_id"] for edge in internal
        )
        summaries.append(
            {
                "members": members,
                "cyclic": cyclic,
                "internal_edges": internal,
                "external_inbound_edges": inbound,
                "external_outbound_edges": outbound,
            }
        )
    return summaries
