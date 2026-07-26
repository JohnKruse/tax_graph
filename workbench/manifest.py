"""Build the deterministic, structure-only review manifest projection."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

import yaml

from workbench.artifacts import ArtifactBundle, GRAPH_OBJECT_KINDS, load_artifact_bundle
from workbench.schema import validate_review_manifest
from workbench.reviewer_language import contains_raw_field_name_token, is_raw_field_name
from workbench.refs import unit_ref_from_address
from workbench.semantics import FormattedSemantics, format_scope_semantics


class ManifestError(ValueError):
    """Raised when published artifacts cannot produce a scoped manifest."""


@dataclass(frozen=True)
class ManifestResult:
    """Result of writing a generated manifest."""

    payload: dict[str, Any]
    path: Path | None


def build_manifest(
    root: str | Path,
    year: str | int,
    *,
    db_path: str | Path | None = None,
    geometry_path: str | Path | None = None,
    queue_path: str | Path | None = None,
    pdf_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Project pending review entries into a stable schema-valid manifest.

    The projection only copies identifiers and relationships from published
    artifacts. It does not compute tax values or invent analog geometry.
    """
    root_path = Path(root).resolve()
    bundle = load_artifact_bundle(
        root_path,
        year,
        db_path=db_path,
        geometry_path=geometry_path,
        queue_path=queue_path,
        pdf_dir=pdf_dir,
    )
    payload = _build_payload(bundle, root_path, db_path=db_path, geometry_path=geometry_path, queue_path=queue_path)
    validate_review_manifest(payload)
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return payload


def write_manifest(
    root: str | Path,
    year: str | int,
    *,
    output_path: str | Path,
    db_path: str | Path | None = None,
    geometry_path: str | Path | None = None,
    queue_path: str | Path | None = None,
    pdf_dir: str | Path | None = None,
) -> ManifestResult:
    """Build and write a manifest, returning both its payload and path."""
    path = Path(output_path).resolve()
    payload = build_manifest(
        root,
        year,
        db_path=db_path,
        geometry_path=geometry_path,
        queue_path=queue_path,
        pdf_dir=pdf_dir,
        output_path=path,
    )
    return ManifestResult(payload=payload, path=path)


def _build_payload(
    bundle: ArtifactBundle,
    root: Path,
    *,
    db_path: str | Path | None,
    geometry_path: str | Path | None,
    queue_path: str | Path | None,
) -> dict[str, Any]:
    graph_index = _graph_index(bundle)
    pdf_hashes = {pdf.path.stem: pdf.sha256 for pdf in bundle.pdfs}
    geometry = bundle.geometry.get("entries", [])
    entries: list[dict[str, Any]] = []
    source_paths: set[Path] = set()
    source_paths.update(
        {
            bundle.graph.path,
            _default_or_given(root / "graph" / str(bundle.tax_year) / "node_geometry.json", geometry_path),
            _default_or_given(
                root / "review_queue" / str(bundle.tax_year) / "deferred_review.yaml",
                queue_path,
            ),
        }
    )
    source_paths.update(pdf.path for pdf in bundle.pdfs)

    for queue_entry in bundle.review_queue.get("entries", []):
        if not isinstance(queue_entry, dict) or not _pending(queue_entry):
            continue
        queue_id = str(queue_entry.get("queue_id", ""))
        scope = queue_entry.get("review_scope")
        if not isinstance(scope, dict) or not isinstance(scope.get("object_refs"), list):
            raise ManifestError(f"pending queue entry {queue_id} has no review scope")
        refs = [ref for ref in scope["object_refs"] if isinstance(ref, dict)]
        if not refs:
            raise ManifestError(f"pending queue entry {queue_id} has an empty review scope")
        units: list[dict[str, Any]] = []
        document_id = str(queue_entry.get("document_id", ""))
        for scope_ref in refs:
            artifact_path = str(scope_ref.get("source_path", ""))
            if artifact_path:
                source_paths.add(root / artifact_path)
            object_ref = _manifest_ref(scope_ref, graph_index)
            object_data = _find_object(graph_index, scope_ref)
            if str(scope_ref.get("object_type")) == "field_control":
                object_data = _field_control_object(root, scope_ref)
                if object_data and object_data.get("label"):
                    object_ref["display_label"] = str(object_data["label"])
            semantics = _semantics(scope_ref, graph_index)
            address_id, identity_source = _resolved_identity_source(
                queue_entry, scope_ref, object_data, graph_index,
            )
            locations = _locations(
                scope_ref,
                geometry,
                pdf_hashes,
                document_id=document_id,
            )
            if not locations:
                locations = [None]
            for location in locations:
                locator = str((location or {}).get("locator_text") or "") if isinstance(location, dict) else ""
                identity_token = str(scope_ref.get("object_id", ""))
                if locator:
                    identity_token = f"{identity_token}|{locator}"
                unit_id = derive_unit_id(
                    address_id=address_id,
                    identity_source=identity_source,
                    document_id=document_id,
                    field_name=_field_name(object_data),
                    review_kind=str(queue_entry.get("kind", "object")),
                    role=str(scope_ref.get("role", "primary")),
                    object_type=str(scope_ref.get("object_type", "object")),
                    object_id=str(scope_ref.get("object_id", "")),
                    identity_token=identity_token,
                )
                units.append(
                    _unit(
                        queue_entry,
                        unit_id=unit_id,
                        scope_ref=scope_ref,
                        object_ref=object_ref,
                        object_data=object_data,
                        graph_index=graph_index,
                        semantics=semantics,
                        location=location,
                        required=_required(scope_ref),
                        address_id=address_id,
                        identity_source=identity_source,
                        identity_role=str(scope_ref.get("role", "primary")),
                        identity_token=identity_token,
                    )
                )
        if not units:
            raise ManifestError(f"pending queue entry {queue_id} produced zero units")
        entries.append(
            {
                "queue_id": queue_id,
                "review_kind": str(queue_entry.get("kind", "object")),
                "status": str(queue_entry.get("status") or queue_entry.get("review_status") or "pending"),
                "summary": str(queue_entry.get("summary", "Review scoped artifacts.")),
                "units": units,
            }
        )

    _validate_unit_id_collisions(entries)

    source_artifacts = _source_artifacts(root, source_paths)
    body = {
        "schema_version": 1,
        "tax_year": bundle.tax_year,
        "source_artifacts": source_artifacts,
        "entries": entries,
    }
    canonical = json.dumps(body, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {**body, "manifest_hash": hashlib.sha256(canonical).hexdigest()}


def _unit(
    queue_entry: dict[str, Any],
    *,
    unit_id: str,
    scope_ref: dict[str, Any],
    object_ref: dict[str, Any],
    object_data: dict[str, Any] | None,
    graph_index: dict[tuple[str, str], dict[str, Any]],
    semantics: FormattedSemantics | None,
    location: dict[str, Any] | None,
    required: bool,
    address_id: str,
    identity_source: str,
    identity_role: str,
    identity_token: str,
) -> dict[str, Any]:
    object_type = str(scope_ref.get("object_type", "object"))
    object_id = str(scope_ref.get("object_id", ""))
    review_kind = str(queue_entry.get("kind", "object"))
    citations = sorted(set(_citation_refs(object_data)) | set(_expression_citations(semantics)))
    address_data = graph_index.get(("address", address_id)) if address_id else None
    address_ref = {"object_type": "address", "object_id": address_id, "display_label": str((address_data or {}).get("printed_label") or address_id)} if address_id else None
    display_name, display_name_provenance, official_locator, review_prompt = _review_identity(
        queue_entry, object_type, object_data, address_data, semantics, location
    )
    unit: dict[str, Any] = {
        "queue_id": str(queue_entry.get("queue_id", "")),
        "unit_id": unit_id,
        "review_kind": review_kind,
        "required": required,
        "object_refs": ([address_ref, object_ref] if address_ref else [object_ref]),
        "official_location": location,
        "analog_placement": None,
        "semantic_class": semantics.semantic_class if semantics else _semantic_class(review_kind, scope_ref, object_data),
        "summary": (
            display_name
            if object_type == "field_control"
            else (semantics.summary if semantics else _unit_summary(queue_entry, object_type, object_data))
        ),
        "display_name": display_name,
        "display_name_provenance": display_name_provenance,
        "official_locator": official_locator,
        "review_prompt": review_prompt,
        "expression": semantics.expression if semantics else {"kind": "reference", "ref": address_ref or object_ref},
        "coverage": {"state": "pending", "required_for_confirm": required},
        "address_status": "addressed" if address_id else "unaddressed",
        "identity_source": identity_source,
        "identity_role": identity_role,
        "identity_qualifier": f"{review_kind}:{identity_role}:{object_type}",
        "identity_token": identity_token,
        "identity_document_id": str(queue_entry.get("document_id") or ""),
        "aliases": [],
    }
    if citations:
        unit["citation_refs"] = citations
    source_refs = _source_refs(object_data, object_type, graph_index=graph_index)
    if source_refs:
        unit["source_refs"] = source_refs
    witnesses = [str(value) for value in queue_entry.get("machine_witnesses", []) or []]
    if witnesses:
        unit["witness_refs"] = witnesses
    if queue_entry.get("verification_tier"):
        unit["trust"] = str(queue_entry["verification_tier"])
    changed = [str(value) for value in queue_entry.get("changed_object_ids", []) or []]
    if changed:
        unit["promotion_diff_refs"] = changed
    if address_id:
        unit["address_id"] = address_id
        ref = unit_ref_from_address(address_id)
        if ref:
            unit["ref"] = ref
    if object_type == "field_control" and isinstance(object_data, dict):
        for key in (
            "field_name", "population_policy", "value_format", "node_id",
            "identity_slot", "runtime_fact_ref", "source_ref", "reason",
            "downstream_effect", "missing_capability", "repeatable", "concept_id",
        ):
            if key in object_data:
                unit[key] = object_data[key]
    return unit


def _unit_summary(
    queue_entry: dict[str, Any], object_type: str, object_data: dict[str, Any] | None
) -> str:
    if object_type == "field_control" and isinstance(object_data, dict):
        return str(object_data.get("label") or object_data.get("field_name") or "Official form control")
    return str(queue_entry.get("summary", "Review scoped artifacts."))


def _review_identity(
    queue_entry: dict[str, Any],
    object_type: str,
    object_data: dict[str, Any] | None,
    address_data: dict[str, Any] | None,
    semantics: FormattedSemantics | None,
    location: dict[str, Any] | None,
) -> tuple[str, str, str, str]:
    """Resolve authored reviewer language without deriving names from ids."""
    if object_type == "field_control":
        authored_label = str((address_data or {}).get("printed_label") or "").strip()
        authored_identity = str((object_data or {}).get("display_name") or "").strip()
        identity_slot = str((object_data or {}).get("identity_slot") or "").strip()
        legacy_label = str((object_data or {}).get("label") or "").strip()
        authored_safe = authored_label and not (
            is_raw_field_name(authored_label) or contains_raw_field_name_token(authored_label)
        )
        if authored_safe:
            display_name, provenance = authored_label, "authored_address"
        elif authored_identity:
            display_name, provenance = authored_identity, "authored_object"
        elif authored_label and legacy_label:
            display_name, provenance = legacy_label, "legacy_mined"
        elif authored_label:
            display_name, provenance = authored_label, "legacy_mined"
        elif identity_slot:
            display_name, provenance = identity_slot, "identity_slot"
        elif legacy_label:
            display_name, provenance = legacy_label, "legacy_mined"
        else:
            raise ManifestError("visible field_control has no reviewer-facing display name")
    else:
        candidates = [
            (address_data or {}).get("printed_label"),
            (object_data or {}).get("label"),
            (object_data or {}).get("title"),
            (object_data or {}).get("question"),
            (object_data or {}).get("description"),
            semantics.summary if semantics else None,
            queue_entry.get("summary"),
        ]
        display_name = next(
            (
                str(value).strip()
                for value in candidates
                if value
                and not is_raw_field_name(str(value))
                and not contains_raw_field_name_token(str(value))
            ),
            "",
        )
        provenance = "authored_object"
        if not display_name:
            raise ManifestError(f"visible {object_type} has no authored reviewer-facing display name")
    official_ref = str((address_data or {}).get("official_ref") or "").strip()
    qualifier = _physical_qualifier(object_data, location)
    if official_ref:
        official_locator = f"{display_name} - {official_ref}"
    elif isinstance(location, dict):
        official_locator = f"{display_name} - page {location['page']}"
    else:
        official_locator = display_name
    if qualifier:
        official_locator = f"{official_locator} - {qualifier}"
    policy = str((object_data or {}).get("population_policy") or "")
    prompt = {
        "user_entered": "Confirm the expected filer-entered fact and format.",
        "imported": "Confirm the imported source and destination field.",
        "copied": "Confirm the copied source and destination field.",
        "computed": "Confirm the calculation, sources, and written result.",
        "decision_required": "Confirm the decision options, citation, and escape hatch.",
        "intentionally_blank": "Confirm why this control is intentionally left blank.",
        "unsupported": "Confirm the missing capability and downstream consequence.",
    }.get(policy, "Confirm that the scoped evidence supports this review item.")
    return display_name, provenance, official_locator, prompt


def _physical_qualifier(
    object_data: dict[str, Any] | None, location: dict[str, Any] | None
) -> str:
    """Return a deterministic reviewer-facing qualifier for a physical repeat."""
    repeatable = (object_data or {}).get("repeatable")
    field_name = str((object_data or {}).get("field_name") or "")
    address_id = str((object_data or {}).get("address_id") or "")
    parts: list[str] = []
    copy_match = re.search(r"\.Copy([A-Za-z0-9]+)\[", field_name)
    if copy_match:
        parts.append(f"Copy {copy_match.group(1)}")
    w2_leaf = re.search(r"\.f[1-6]_([0-9]{2})\[0\]$", field_name)
    if w2_leaf and address_id.startswith("2025/document=form_w2/"):
        w2_number = int(w2_leaf.group(1))
        if 20 <= w2_number <= 27:
            parts.append(f"Box 12 row {(w2_number - 20) // 2 + 1}")
        elif 29 <= w2_number <= 42:
            row = (1 if w2_number <= 30 else 2) if w2_number <= 32 else (1 if w2_number % 2 else 2)
            parts.append(f"state/local row {row}")
    # The Form 1040 "Other" filing-designation write-in is one logical control split
    # across three physical AcroForm segments; each unit needs a distinct locator.
    if address_id.endswith("/section=return_header/control=other_filing_designation_text"):
        segment = re.search(r"\.f1_1([1-3])\[0\]$", field_name)
        if segment:
            parts.append(f"segment {int(segment.group(1)) - 10}")
    info_return_leaf = re.search(r"\.f[12]_([0-9]+)\[0\]$", field_name)
    state_ranges = {
        "2025/document=form_1099b/": range(9, 15),
        "2025/document=form_1099_div/": range(27, 33),
        "2025/document=form_1099_int/": range(23, 29),
    }
    if info_return_leaf:
        field_number = int(info_return_leaf.group(1))
        for prefix, field_range in state_ranges.items():
            if address_id.startswith(prefix) and field_number in field_range:
                parts.append(f"state row {1 if field_number % 2 else 2}")
                break
    schedule_1a_row = re.search(r"\.Line22([ab])\[", field_name)
    if address_id.startswith("2025/document=schedule_1a/table=line_22/") and schedule_1a_row:
        parts.append(f"line 22 row {schedule_1a_row.group(1)}")
    row_slot = repeatable.get("row_slot") if isinstance(repeatable, dict) else None
    row_match = re.search(r"\.(?:Body)?Row(\d+)\[", field_name)
    if row_slot is not None:
        part = "Part II" if ".Page2[" in field_name or "Part2[" in field_name else "Part I"
        parts.append(f"{part} row {row_slot}")
    elif row_match:
        parts.append(f"row {row_match.group(1)}")
    elif re.search(r"\.Page1\[.*\.f1_0[12]\[", field_name):
        parts.append("Part I")
    elif re.search(r"\.Page2\[.*\.f2_0[12]\[", field_name):
        parts.append("Part II")
    elif re.search(r"\.Page1\[.*\.f1_9[1-5]\[", field_name):
        parts.append("Part I totals row")
    elif re.search(r"\.Page2\[.*\.f2_9[1-5]\[", field_name):
        parts.append("Part II totals row")
    leaf_index = re.search(r"\.(?:[A-Za-z0-9_-]+)\[(\d+)\]$", field_name)
    if leaf_index and int(leaf_index.group(1)) > 0:
        parts.append(f"choice {int(leaf_index.group(1)) + 1}")
    if parts:
        return ", ".join(parts)
    return ""


def _field_control_object(root: Path, scope_ref: dict[str, Any]) -> dict[str, Any] | None:
    source = root / str(scope_ref.get("source_path", ""))
    if not source.is_file():
        return None
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    object_id = str(scope_ref.get("object_id", ""))
    return next(
        (
            dict(item)
            for item in payload.get("field_dispositions", []) or []
            if isinstance(item, dict) and str(item.get("field_name")) == object_id
        ),
        None,
    )


def _manifest_ref(scope_ref: dict[str, Any], graph_index: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    object_type = str(scope_ref.get("object_type", ""))
    object_id = str(scope_ref.get("object_id", ""))
    if not object_type or not object_id:
        raise ManifestError("review scope contains an incomplete object reference")
    result: dict[str, Any] = {"object_type": object_type, "object_id": object_id}
    if scope_ref.get("source_path"):
        result["artifact_path"] = str(scope_ref["source_path"])
    object_data = graph_index.get((object_type, object_id))
    label = _display_label(object_data, object_id)
    if label:
        result["display_label"] = label
    return result


def _locations(
    scope_ref: dict[str, Any],
    geometry: Iterable[dict[str, Any]],
    pdf_hashes: dict[str, str],
    *,
    document_id: str = "",
) -> list[dict[str, Any]]:
    object_type = str(scope_ref.get("object_type", ""))
    object_id = str(scope_ref.get("object_id", ""))
    base_id = object_id.split("#", 1)[0]
    matches: list[dict[str, Any]] = []
    for entry in geometry:
        if not isinstance(entry, dict):
            continue
        if document_id and str(entry.get("document_id", "")) != document_id:
            continue
        node_match = object_type in {"node", "node_instance"} and entry.get("node_id") == base_id
        field_match = object_type in {"field", "field_inventory", "field_control"} and (
            entry.get("identity_slot") == object_id or entry.get("field_name") == object_id
        )
        if not (node_match or field_match):
            continue
        document_id = str(entry.get("document_id", ""))
        source_hash = pdf_hashes.get(document_id)
        if not source_hash:
            continue
        location: dict[str, Any] = {
            "document_id": document_id,
            "source_pdf_hash": source_hash,
            "page": int(entry["page"]),
            "rect": [float(value) for value in entry["rect"]],
        }
        if entry.get("address_id"):
            location["address_id"] = str(entry["address_id"])
        locator = entry.get("field_name") or entry.get("slot") or entry.get("identity_slot")
        if locator:
            location["locator_text"] = str(locator)
        matches.append(location)
    return matches


def _graph_index(bundle: ArtifactBundle) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for kind in GRAPH_OBJECT_KINDS:
        object_type = kind[:-1] if kind.endswith("s") else kind
        for obj in bundle.graph.objects(kind):
            object_id = _object_id(object_type, obj)
            if object_id:
                result[(object_type, object_id)] = obj
            if object_type == "decision":
                for option in obj.get("options", []) or []:
                    if isinstance(option, dict) and option.get("option_id"):
                        result[("decision_option", str(option["option_id"]))] = option
    graph_dir = bundle.root / "graph" / str(bundle.tax_year)
    for path in sorted((graph_dir / "addresses").glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for item in payload.get("addresses", []):
            result[("address", str(item["address_id"]))] = item
    for path in sorted((graph_dir / "bindings" / "nodes").glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for item in payload.get("bindings", []):
            result[("node_binding", str(item["node_id"]))] = item
    for path in sorted((graph_dir / "bindings" / "widgets").glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        document_id = str(payload.get("document_id") or "")
        for item in payload.get("bindings", []):
            key = f"{document_id}\0{item['field_name']}"
            result[("widget_binding", key)] = item
    return result


def _object_id(object_type: str, obj: dict[str, Any]) -> str | None:
    key = {
        "document": "document_id",
        "node": "node_id",
        "table": "table_id",
        "edge": "edge_id",
        "rule": "rule_id",
        "citation": "citation_id",
        "decision": "decision_id",
        "routing_edge": "routing_id",
        "trigger": "trigger_id",
        "expectation": "expectation_id",
    }.get(object_type)
    value = obj.get(key) if key else None
    return str(value) if value is not None else None


def _find_object(
    graph_index: dict[tuple[str, str], dict[str, Any]],
    scope_ref: dict[str, Any],
) -> dict[str, Any] | None:
    return graph_index.get((str(scope_ref.get("object_type", "")), str(scope_ref.get("object_id", ""))))


def _semantics(
    scope_ref: dict[str, Any],
    graph_index: dict[tuple[str, str], dict[str, Any]],
) -> FormattedSemantics | None:
    return format_scope_semantics(scope_ref, graph_index)


def _citation_refs(object_data: dict[str, Any] | None) -> list[str]:
    if not isinstance(object_data, dict):
        return []
    return sorted({str(value) for value in object_data.get("citation_refs", []) or []})


def _expression_citations(semantics: FormattedSemantics | None) -> list[str]:
    """Collect citations from every level of a formatted expression tree."""
    if semantics is None:
        return []
    citations: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            citations.update(str(item) for item in value.get("citation_refs", []) or [])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(semantics.expression)
    return sorted(citations)


def _source_refs(
    object_data: dict[str, Any] | None,
    object_type: str,
    graph_index: dict[tuple[str, str], dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if object_type != "edge" or not isinstance(object_data, dict):
        return []
    refs: list[dict[str, Any]] = []
    for direction, key in (("source", "source"), ("target", "target")):
        value = object_data.get(key)
        if value:
            ref: dict[str, Any] = {
                "direction": direction,
                "object_type": "node",
                "object_id": str(value),
            }
            if graph_index is not None:
                ref["display_label"] = _display_label(
                    graph_index.get(("node", str(value))),
                    str(value),
                )
            refs.append(ref)
    return refs


def _semantic_class(review_kind: str, scope_ref: dict[str, Any], object_data: dict[str, Any] | None) -> str:
    object_type = str(scope_ref.get("object_type", ""))
    role = str(scope_ref.get("role", ""))
    if review_kind.startswith("field_map") or object_type in {"field", "field_inventory"}:
        policy = str((object_data or {}).get("population_policy", ""))
        return {
            "user_entered": "input",
            "imported": "imported",
            "copied": "copy",
            "computed": "calculation",
            "decision_required": "decision",
            "intentionally_blank": "review_gap",
            "unsupported": "review_gap",
        }.get(policy, "field_map")
    if review_kind.startswith("intake") or object_type in {"routing_edge", "trigger", "expectation"}:
        return "contract"
    if review_kind.startswith("decision") or object_type in {"decision", "decision_option"}:
        return "decision"
    if review_kind.startswith("frontier") or role in {"frontier", "excluded"} or object_type.startswith("frontier"):
        return "frontier"
    if review_kind.startswith("irs_example") or object_type == "node_instance":
        return "example"
    if object_type == "citation":
        return "citation"
    if object_type == "rule" and isinstance(object_data, dict):
        operation = str(object_data.get("operation", "")).upper()
        if operation in {"LOOKUP_TABLE", "LOOKUP_BRACKET"}:
            return "lookup"
        if operation in {"IF_ELSE", "MAX", "MIN"}:
            return "branch"
    return "calculation"


def _display_label(object_data: dict[str, Any] | None, fallback: str) -> str:
    if not isinstance(object_data, dict):
        return fallback
    for key in ("label", "title", "question", "description", "relationship"):
        value = object_data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _required(scope_ref: dict[str, Any]) -> bool:
    return str(scope_ref.get("role", "primary")) in {"primary", "expected"}


def _pending(entry: dict[str, Any]) -> bool:
    return str(entry.get("status", "")) == "pending" or str(entry.get("review_status", "")) == "pending"


def _field_name(object_data: dict[str, Any] | None) -> str:
    """Return the stable AcroForm field name when the object has one."""
    return str(object_data.get("field_name") or "") if isinstance(object_data, dict) else ""


def _resolved_identity_source(
    queue_entry: dict[str, Any],
    scope_ref: dict[str, Any],
    object_data: dict[str, Any] | None,
    graph_index: dict[tuple[str, str], dict[str, Any]],
) -> tuple[str, str]:
    """Resolve an address, or a stable within-year fallback for an unaddressed unit."""
    object_type = str(scope_ref.get("object_type", "object"))
    object_id = str(scope_ref.get("object_id", ""))
    address_id = str(object_data.get("address_id", "")) if isinstance(object_data, dict) else ""
    if object_type == "node" and not address_id:
        binding = graph_index.get(("node_binding", object_id))
        if binding:
            address_id = str(binding.get("address_id") or "")
    if object_type == "field_control" and isinstance(object_data, dict):
        field_name = _field_name(object_data)
        document_id = str(queue_entry.get("document_id") or "")
        binding = graph_index.get(("widget_binding", f"{document_id}\0{field_name}"))
        if binding:
            address_id = str(binding.get("address_id") or "")
    if address_id:
        return address_id, "address_id"
    if _field_name(object_data):
        return "", "field_name"
    if object_id:
        return "", "object_id"
    raise ManifestError(
        "unaddressed review unit has neither a field_name nor a stable object_id"
    )


def _identity_source_key(
    *,
    address_id: str,
    identity_source: str,
    document_id: str,
    field_name: str,
    object_type: str,
    object_id: str,
) -> str:
    """Serialize the non-positional identity input used to derive a unit id."""
    if address_id:
        return f"address:{address_id}"
    if identity_source == "field_name" and field_name:
        return f"field:{document_id}:{field_name}"
    if identity_source == "object_id" and object_id:
        return f"object:{document_id}:{object_type}:{object_id}"
    raise ManifestError("cannot derive a review unit identity without a stable source")


def derive_unit_id(
    *,
    address_id: str,
    identity_source: str,
    document_id: str,
    field_name: str,
    review_kind: str,
    role: str,
    object_type: str,
    object_id: str,
    identity_token: str = "",
) -> str:
    """Derive a deterministic, non-positional review-unit id.

    The digest is deliberately based on the canonical address when one exists.
    Unaddressed controls use their document-qualified AcroForm field name and
    remain visibly unaddressed in the manifest. Review kind, scope role, and
    object type keep distinct reviews of the same address from collapsing.
    """
    source = _identity_source_key(
        address_id=address_id,
        identity_source=identity_source,
        document_id=document_id,
        field_name=field_name,
        object_type=object_type,
        object_id=object_id,
    )
    qualifier = f"{review_kind}:{role}:{object_type}:{identity_token or object_id}"
    digest = hashlib.sha256(f"{source}|{qualifier}".encode("utf-8")).hexdigest()
    prefix = "address" if address_id else "unaddressed"
    return f"unit_{prefix}_{digest}"


def unit_identity_key(unit: dict[str, Any]) -> str | None:
    """Return the migration key for a projected unit, without using its id."""
    address_id = str(unit.get("address_id") or "")
    identity_source = str(unit.get("identity_source") or ("address_id" if address_id else ""))
    location = unit.get("official_location")
    document_id = str(unit.get("identity_document_id") or "")
    if not document_id and isinstance(location, dict):
        document_id = str(location.get("document_id") or "")
    object_refs = [ref for ref in unit.get("object_refs", []) or [] if isinstance(ref, dict)]
    object_ref = next((ref for ref in object_refs if ref.get("object_type") != "address"), {})
    object_type = str(object_ref.get("object_type") or "object")
    object_id = str(object_ref.get("object_id") or "")
    field_name = str(unit.get("field_name") or object_id if object_type == "field_control" else "")
    identity_token = str(unit.get("identity_token") or object_id)
    if not unit.get("identity_token") and isinstance(location, dict):
        locator = str(location.get("locator_text") or "")
        if locator:
            identity_token = f"{identity_token}|{locator}"
    if not document_id and address_id:
        document_id = next(
            (part.split("=", 1)[1] for part in address_id.split("/") if part.startswith("document=")),
            "",
        )
    try:
        source = _identity_source_key(
            address_id=address_id,
            identity_source=identity_source,
            document_id=document_id,
            field_name=field_name,
            object_type=object_type,
            object_id=object_id,
        )
    except ManifestError:
        return None
    qualifier = unit.get("identity_qualifier")
    if not qualifier:
        role = str(unit.get("identity_role") or "primary")
        qualifier = f"{unit.get('review_kind', 'object')}:{role}:{object_type}:{object_id}"
    return f"{source}|{qualifier}|{identity_token}"


def _validate_unit_id_collisions(entries: Iterable[dict[str, Any]]) -> None:
    """Fail closed on duplicate or position-derived ids within a document."""
    seen: dict[tuple[str, str], tuple[str, str]] = {}
    positional = re.compile(r"(?:^|_)(?:ref|loc)(?:_|\d)(?:[a-z0-9_]*\d)?(?:_|$)")
    for entry in entries:
        for unit in entry.get("units", []) or []:
            unit_id = str(unit.get("unit_id") or "")
            if positional.search(unit_id):
                raise ManifestError(f"review unit id is positional: {unit_id}")
            location = unit.get("official_location")
            document_id = str((location or {}).get("document_id") or "") if isinstance(location, dict) else ""
            if not document_id:
                address_id = str(unit.get("address_id") or "")
                document_id = next(
                    (part.split("=", 1)[1] for part in address_id.split("/") if part.startswith("document=")),
                    "",
                )
            key = (document_id, unit_id)
            identity = unit_identity_key(unit) or "unknown"
            previous = seen.get(key)
            if previous is not None and previous[1] != identity:
                raise ManifestError(
                    f"review unit id collision in {document_id or 'unknown document'}: {unit_id}"
                )
            if previous is not None:
                raise ManifestError(
                    f"duplicate review unit identity in {document_id or 'unknown document'}: {unit_id}"
                )
            seen[key] = (document_id, identity)


def _source_artifacts(root: Path, paths: Iterable[Path]) -> list[dict[str, str]]:
    files: set[Path] = set()
    for path in {item.resolve() for item in paths}:
        if path.is_file():
            files.add(path)
        elif path.is_dir():
            files.update(item.resolve() for item in path.rglob("*") if item.is_file())
        else:
            raise ManifestError(f"review source artifact does not exist: {path}")

    artifacts: list[dict[str, str]] = []
    for path in sorted(files):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = path.as_posix()
        artifacts.append({"path": relative, "content_hash": digest})
    return artifacts


def _default_or_given(default: Path, given: str | Path | None) -> Path:
    return Path(given).resolve() if given is not None else default.resolve()
