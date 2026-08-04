"""M20 S45 tests for address-ledger to graph-node flag projection."""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest
import yaml

from tax_graph.review import apply_address_verdicts
from workbench.address_verdicts import append_address_verdict, make_review_content


ROOT = Path(__file__).resolve().parents[1]
ADDRESS = "2025/document=form_a/line=1/control=amount"

pytestmark = pytest.mark.m20


def _fixture_root(tmp_path: Path, *, node_ids: tuple[str, ...] = ("node_a",)) -> Path:
    for name in ("address_registry.schema.json", "address_binding.schema.json"):
        (tmp_path / "schemas").mkdir(exist_ok=True)
        shutil.copy(ROOT / "schemas" / name, tmp_path / "schemas" / name)

    graph = tmp_path / "graph" / "2025"
    for name in ("nodes", "addresses"):
        (graph / name).mkdir(parents=True, exist_ok=True)
    (graph / "bindings" / "nodes").mkdir(parents=True, exist_ok=True)

    nodes = [
        {
            "node_id": node_id,
            "document_id": "form_a_2025",
            "label": "Amount",
            "node_type": "form_line",
            "value_type": "currency",
        }
        for node_id in node_ids
    ]
    (graph / "nodes" / "review.yaml").write_text(
        yaml.safe_dump(nodes, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )

    evidence = {"source_path": "tests/fixture", "source_hash": "0" * 64, "page": 1}
    addresses = [
        {
            "address_id": "2025/document=form_a",
            "logical_key": "document=form_a",
            "year": 2025,
            "document_id": "form_a_2025",
            "parent_address_id": None,
            "kind": "document",
            "path": [{"kind": "document", "token": "form_a"}],
            "printed_label": "Form A",
            "aliases": [],
            "control_role": "none",
            "status": "confirmed",
            "evidence": [evidence],
        },
        {
            "address_id": "2025/document=form_a/line=1",
            "logical_key": "document=form_a/line=1",
            "year": 2025,
            "document_id": "form_a_2025",
            "parent_address_id": "2025/document=form_a",
            "kind": "line",
            "path": [
                {"kind": "document", "token": "form_a"},
                {"kind": "line", "token": "1"},
            ],
            "printed_label": "Line 1",
            "aliases": [],
            "control_role": "none",
            "status": "confirmed",
            "evidence": [evidence],
            "official_ref": "1",
        },
        {
            "address_id": ADDRESS,
            "logical_key": "document=form_a/line=1/control=amount",
            "year": 2025,
            "document_id": "form_a_2025",
            "parent_address_id": "2025/document=form_a/line=1",
            "kind": "control",
            "path": [
                {"kind": "document", "token": "form_a"},
                {"kind": "line", "token": "1"},
                {"kind": "control", "token": "amount"},
            ],
            "printed_label": "Amount",
            "aliases": [],
            "control_role": "amount",
            "status": "confirmed",
            "evidence": [evidence],
            "official_ref": "1",
        },
    ]
    (graph / "addresses" / "form_a_2025.yaml").write_text(
        yaml.safe_dump(
            {"schema_version": 1, "year": 2025, "document_id": "form_a_2025", "addresses": addresses},
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )

    bindings = [
        {
            "node_id": node_id,
            "address_id": ADDRESS,
            "expected_official_ref": "1",
            "role": "value",
            "status": "exact",
        }
        for node_id in node_ids
    ]
    (graph / "bindings" / "nodes" / "form_a_2025.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "year": 2025,
                "document_id": "form_a_2025",
                "binding_kind": "node",
                "bindings": bindings,
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    return tmp_path


def _unit(address: str = ADDRESS, label: str = "Amount") -> dict[str, object]:
    expression = {"kind": "input", "text": f"Input: {label}"}
    return {
        "address_id": address,
        "review_content": make_review_content(
            label,
            expression=expression,
            form_citations=["Enter amount."],
        ),
    }


def _append(root: Path, *, judgement: str = "confirmed", label: str = "Amount") -> Path:
    path = root / "address_verdicts.jsonl"
    unit = _unit(label=label)
    append_address_verdict(
        root=root,
        year=2025,
        address=ADDRESS,
        label=label,
        expression=unit["review_content"]["expression"],
        form_citations=["Enter amount."],
        judgement=judgement,
        reviewer_id="john",
        reviewed_at="2026-08-04T12:00:00Z",
        verdict_id="verdict_" + judgement,
        store_path=path,
    )
    return path


def test_confirmed_address_verdict_is_dry_run_then_uses_existing_applier(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    path = _append(root)
    units = [_unit()]
    node_path = root / "graph" / "2025" / "nodes" / "review.yaml"

    dry = apply_address_verdicts(
        2025, root=root, ledger_path=path, current_units=units,
    )
    assert dry.would_apply == ("verdict_confirmed",)
    assert dry.applied == ()
    report = dry.reports[0]
    assert report["status"] == "would_apply"
    assert report["address_resolution"] == "exact"
    assert report["node_binding_resolution"] == "exact"
    assert [item["field"] for item in report["field_changes"]] == [
        "human_confirmed", "verification_tier", "human_review",
    ]
    assert "human_confirmed" not in node_path.read_text(encoding="utf-8")

    applied = apply_address_verdicts(
        2025, root=root, ledger_path=path, dry_run=False, current_units=units,
    )
    assert applied.applied == ("verdict_confirmed",)
    node = yaml.safe_load(node_path.read_text(encoding="utf-8"))[0]
    assert node["human_confirmed"] is True
    assert node["verification_tier"] == "human-confirmed"
    assert node["human_review"]["verdict"] == "confirmed"


def test_stale_address_verdict_names_both_fingerprints_and_does_not_apply(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    path = _append(root, label="Amount")
    node_path = root / "graph" / "2025" / "nodes" / "review.yaml"

    result = apply_address_verdicts(
        2025,
        root=root,
        ledger_path=path,
        dry_run=False,
        current_units=[_unit(label="Changed amount")],
    )
    assert result.stale == ("verdict_confirmed",)
    assert result.applied == ()
    report = result.reports[0]
    assert report["status"] == "stale"
    assert report["reviewed_fingerprint"] != report["current_fingerprint"]
    assert "human_confirmed" not in node_path.read_text(encoding="utf-8")


def test_multiple_node_bindings_are_ambiguous_and_never_confirmed(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path, node_ids=("node_a", "node_b"))
    path = _append(root)

    result = apply_address_verdicts(
        2025, root=root, ledger_path=path, dry_run=False, current_units=[_unit()],
    )
    assert result.ambiguous == ("verdict_confirmed",)
    assert result.reports[0]["status"] == "node_binding_ambiguous"
    assert result.reports[0]["node_ids"] == ["node_a", "node_b"]
    assert "human_confirmed" not in (root / "graph" / "2025" / "nodes" / "review.yaml").read_text(encoding="utf-8")


@pytest.mark.parametrize("judgement", ["rejected", "problem"])
def test_non_confirming_judgements_are_reported_without_inventing_node_flags(
    tmp_path: Path,
    judgement: str,
) -> None:
    root = _fixture_root(tmp_path)
    path = _append(root, judgement=judgement)

    result = apply_address_verdicts(
        2025, root=root, ledger_path=path, dry_run=False, current_units=[_unit()],
    )
    assert result.unsupported_judgements == ("verdict_" + judgement,)
    assert result.reports[0]["status"] == "unsupported_judgement"
    assert result.reports[0]["supported_judgements"] == ["confirmed"]
    assert "human_confirmed" not in (root / "graph" / "2025" / "nodes" / "review.yaml").read_text(encoding="utf-8")
