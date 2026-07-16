"""Deterministic document-first navigation for review manifest units."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping


CHECK_GROUPS = (
    ("identity_inputs", "Identity and filer inputs"),
    ("mappings_imports", "Mappings and imports"),
    ("calculations", "Calculations"),
    ("decisions", "Decisions"),
    ("tables_worksheets", "Tables and worksheets"),
    ("citations_witnesses", "Citations and witnesses"),
    ("diffs", "Changes and diffs"),
    ("unsupported_gaps", "Unsupported and review gaps"),
)


def build_document_navigation(
    entries: Iterable[Mapping[str, Any]],
    documents: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Project authoritative queue units into stable document/check groups.

    Every review unit occurs exactly once. Units without page geometry inherit a
    document only when their queue entry has one unambiguous located document;
    otherwise they remain in an honest cross-document review bucket.
    """
    titles = {
        str(item.get("document_id")): str(item.get("title") or item.get("document_id"))
        for item in documents
        if item.get("document_id")
    }
    projected: dict[str, dict[str, Any]] = {}
    for entry in sorted(entries, key=lambda item: str(item.get("queue_id", ""))):
        units = list(entry.get("units", []) or [])
        located_documents = sorted({
            str(location["document_id"])
            for unit in units
            if isinstance((location := unit.get("official_location")), Mapping)
            and location.get("document_id")
        })
        inherited = (
            located_documents[0]
            if len(located_documents) == 1
            else _infer_document_id(entry, titles)
        )
        for unit in sorted(units, key=lambda item: str(item.get("unit_id", ""))):
            location = unit.get("official_location")
            document_id = (
                str(location["document_id"])
                if isinstance(location, Mapping) and location.get("document_id")
                else inherited
            )
            document = projected.setdefault(document_id, {
                "document_id": document_id,
                "title": titles.get(document_id, "Cross-document and source review"),
                "pages": set(),
                "units": [],
            })
            if isinstance(location, Mapping) and location.get("page") is not None:
                document["pages"].add(int(location["page"]))
            document["units"].append((entry, unit))

    result = []
    for document_id, raw in projected.items():
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry, unit in raw["units"]:
            grouped[_check_group(entry, unit)].append({
                "queue_id": str(entry["queue_id"]),
                "unit_id": str(unit["unit_id"]),
                "required": bool(unit.get("required")),
                "page": (
                    int(unit["official_location"]["page"])
                    if isinstance(unit.get("official_location"), Mapping)
                    else None
                ),
            })
        check_groups = []
        for group_id, label in CHECK_GROUPS:
            refs = sorted(grouped.get(group_id, []), key=lambda item: (item["queue_id"], item["unit_id"]))
            if not refs:
                continue
            check_groups.append({
                "group_id": group_id,
                "label": label,
                "counts": _counts(refs),
                "unit_refs": refs,
            })
        all_refs = [ref for group in check_groups for ref in group["unit_refs"]]
        result.append({
            "document_id": document_id,
            "title": raw["title"],
            "pages": sorted(raw["pages"]),
            "counts": _counts(all_refs),
            "status": "pending" if any(ref["required"] for ref in all_refs) else "available",
            "check_groups": check_groups,
        })
    return sorted(result, key=lambda item: (item["document_id"] == "unlocated", item["title"], item["document_id"]))


def _counts(refs: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    items = list(refs)
    return {
        "required": sum(bool(item.get("required")) for item in items),
        "visited": 0,
        "accepted": 0,
        "correction": 0,
        "total": len(items),
    }


def _infer_document_id(entry: Mapping[str, Any], titles: Mapping[str, str]) -> str:
    """Resolve an unlocated entry only from explicit authored identifiers."""
    haystacks = [str(entry.get("queue_id") or "")]
    for unit in entry.get("units", []) or []:
        for ref in unit.get("object_refs", []) or []:
            if isinstance(ref, Mapping):
                haystacks.extend(str(ref.get(key) or "") for key in ("object_id", "artifact_path"))
    matches = {
        document_id
        for document_id in titles
        if any(document_id in value for value in haystacks)
    }
    return max(matches, key=len) if matches else "unlocated"


def _check_group(entry: Mapping[str, Any], unit: Mapping[str, Any]) -> str:
    policy = str(unit.get("field_policy") or "")
    semantic = str(unit.get("semantic_class") or "")
    review_kind = str(entry.get("review_kind") or "")
    refs = list(unit.get("object_refs", []) or [])
    ref_types = {str(ref.get("object_type")) for ref in refs if isinstance(ref, Mapping)}
    if policy == "unsupported" or semantic in {"frontier", "gap", "unsupported"} or "frontier" in review_kind:
        return "unsupported_gaps"
    if policy == "decision_required" or semantic == "decision" or "decision" in review_kind:
        return "decisions"
    if semantic in {"table", "worksheet", "worksheet_step"} or "worksheet" in review_kind:
        return "tables_worksheets"
    if "promotion" in review_kind or semantic == "diff":
        return "diffs"
    if ref_types & {"citation", "flow_review"} or "nversion" in review_kind or "example" in review_kind:
        return "citations_witnesses"
    if policy == "user_entered" or semantic in {"input", "filer_input"}:
        return "identity_inputs"
    if policy in {"imported", "copied"} or semantic in {"copy", "imported", "mapping"}:
        return "mappings_imports"
    return "calculations"
