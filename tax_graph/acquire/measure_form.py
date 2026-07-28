"""Measure form text retention and probe PDF producer layers.

The PDF text layer is the ground truth for this measurement. The shipped form
renderer is measured in memory so the command never overwrites the acquired
raw text that citation checks validate.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from tax_graph.acquire.render_form import extract_line_markdown
from tax_graph.io.loader import load_yaml


WORD_TOKEN_RE = re.compile(r"(?:\$[0-9][0-9,]*(?:\.[0-9]+)?|[a-z0-9%]+)", re.IGNORECASE)
EXPECTED_HEADLINE_RETENTION = {
    "form_13614_c_2025": 17.0,
    "form_1040_2025": 52.0,
    "schedule_3_2025": 85.7,
}
EXPECTED_MEAN_RETENTION = 52.2


@dataclass(frozen=True)
class FormMeasurement:
    """One PDF measurement, including all three producer-layer probes."""

    document_id: str
    source_path: str
    sha256: str
    producer: str | None
    creator: str | None
    page_count: int
    widget_count: int
    table_count: int | None
    table_probe_status: str
    ground_truth_words: int
    shipped_words: int
    preserved_words: int
    missing_words: int
    fabricated_words: int
    retention: float
    fabrication: float

    @property
    def layers(self) -> dict[str, dict[str, Any]]:
        """Return explicit present/absent results for the robustness layers."""
        return {
            "text": {
                "status": "present" if self.ground_truth_words else "absent",
                "word_count": self.ground_truth_words,
            },
            "widgets": {
                "status": "present" if self.widget_count else "absent",
                "count": self.widget_count,
            },
            "structure": {
                "status": (
                    "present"
                    if self.table_probe_status == "ok" and (self.table_count or 0) > 0
                    else self.table_probe_status if self.table_probe_status != "ok" else "absent"
                ),
                "table_count": self.table_count,
            },
        }

    def as_dict(self) -> dict[str, Any]:
        """Serialize the measurement with the layer result included."""
        payload = asdict(self)
        payload["layers"] = self.layers
        return payload


def measure_form_pdf(pdf_path: str | Path, *, document_id: str | None = None, source_path: str | None = None) -> FormMeasurement:
    """Measure one PDF against its own PyMuPDF text layer."""
    import fitz

    path = Path(pdf_path)
    with fitz.open(path) as document:
        ground_truth = "\n".join(page.get_text() for page in document)
        page_count = len(document)
        widget_count = sum(len(list(page.widgets() or ())) for page in document)
        table_count, table_probe_status = _count_tables(document)
        metadata = document.metadata or {}

    shipped = extract_line_markdown(path)
    truth_tokens = _word_counter(ground_truth)
    shipped_tokens = _word_counter(shipped)
    preserved = sum((truth_tokens & shipped_tokens).values())
    missing = sum((truth_tokens - shipped_tokens).values())
    fabricated = sum((shipped_tokens - truth_tokens).values())
    truth_count = sum(truth_tokens.values())
    shipped_count = sum(shipped_tokens.values())

    return FormMeasurement(
        document_id=document_id or path.stem,
        source_path=source_path or str(path),
        sha256=_sha256(path),
        producer=_metadata_value(metadata, "producer"),
        creator=_metadata_value(metadata, "creator"),
        page_count=page_count,
        widget_count=widget_count,
        table_count=table_count,
        table_probe_status=table_probe_status,
        ground_truth_words=truth_count,
        shipped_words=shipped_count,
        preserved_words=preserved,
        missing_words=missing,
        fabricated_words=fabricated,
        retention=preserved / truth_count if truth_count else 1.0,
        fabrication=fabricated / shipped_count if shipped_count else 0.0,
    )


def load_robustness_manifest(corpus_dir: str | Path) -> list[dict[str, str]]:
    """Load and validate the separate producer-robustness corpus manifest."""
    root = Path(corpus_dir)
    path = root / "manifest.yaml"
    payload = load_yaml(path)
    entries = payload.get("documents") if isinstance(payload, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"robustness manifest must contain documents: {path}")
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError(f"robustness manifest entries must be mappings: {path}")
        document_id = str(item.get("document_id") or "")
        filename = str(item.get("filename") or "")
        source_url = str(item.get("source_url") or "")
        expected_sha256 = str(item.get("sha256") or "").lower()
        if not document_id or not filename or not source_url or len(expected_sha256) != 64:
            raise ValueError(f"robustness manifest entry is incomplete: {path}")
        if document_id in seen:
            raise ValueError(f"duplicate robustness document_id: {document_id}")
        pdf_path = root / filename
        if not pdf_path.is_file():
            raise FileNotFoundError(f"robustness PDF is missing: {pdf_path}")
        actual_sha256 = _sha256(pdf_path)
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"robustness PDF hash mismatch for {document_id}: expected {expected_sha256}, got {actual_sha256}"
            )
        seen.add(document_id)
        result.append(
            {
                "document_id": document_id,
                "filename": filename,
                "source_url": source_url,
                "sha256": expected_sha256,
            }
        )
    return result


def measure_directory(
    pdf_dir: str | Path,
    *,
    root: str | Path | None = None,
    exclude_prefixes: Iterable[str] = ("instructions_",),
) -> list[FormMeasurement]:
    """Measure form PDFs in a directory without writing beside the inputs."""
    directory = Path(pdf_dir)
    root_path = Path(root).resolve() if root is not None else None
    prefixes = tuple(exclude_prefixes)
    measurements: list[FormMeasurement] = []
    for path in sorted(directory.glob("*.pdf")):
        if path.name.startswith(prefixes):
            continue
        source = _display_path(path, root_path)
        measurements.append(measure_form_pdf(path, document_id=path.stem, source_path=source))
    if not measurements:
        raise FileNotFoundError(f"no form PDFs found in {directory}")
    return measurements


def measure_robustness_corpus(corpus_dir: str | Path, *, root: str | Path | None = None) -> list[FormMeasurement]:
    """Measure each separately acquired producer-robustness PDF."""
    corpus_root = Path(corpus_dir)
    root_path = Path(root).resolve() if root is not None else None
    measurements = []
    for entry in load_robustness_manifest(corpus_root):
        path = corpus_root / entry["filename"]
        measurements.append(
            measure_form_pdf(
                path,
                document_id=entry["document_id"],
                source_path=_display_path(path, root_path),
            )
        )
    return measurements


def build_snapshot(
    measurements: Iterable[FormMeasurement],
    *,
    robustness: Iterable[FormMeasurement] = (),
    source_directory: str | None = None,
    corpus_directory: str | None = None,
) -> dict[str, Any]:
    """Build a stable, thresholdable JSON snapshot."""
    forms = list(measurements)
    corpus = list(robustness)
    mean_retention = sum(item.retention for item in forms) / len(forms) if forms else 0.0
    by_id = {item.document_id: item for item in forms}
    headline = {}
    for key, expected in EXPECTED_HEADLINE_RETENTION.items():
        item = by_id.get(key)
        measured = round(item.retention * 100, 1) if item is not None else None
        headline[key] = {
            "measured_percent": measured,
            "expected_percent": expected,
            "reproduced": measured == expected,
        }
    return {
        "schema_version": 1,
        "ground_truth": "PyMuPDF page.get_text()",
        "token_pattern": WORD_TOKEN_RE.pattern,
        "metric": "lowercase word-multiset intersection and difference",
        "source_directory": source_directory,
        "corpus_directory": corpus_directory,
        "form_count": len(forms),
        "mean_retention_percent": round(mean_retention * 100, 1),
        "expected_mean_retention_percent": EXPECTED_MEAN_RETENTION,
        "mean_reproduced": round(mean_retention * 100, 1) == EXPECTED_MEAN_RETENTION,
        "headline": headline,
        "forms": [item.as_dict() for item in forms],
        "robustness_corpus": [item.as_dict() for item in corpus],
    }


def render_snapshot_markdown(snapshot: dict[str, Any]) -> str:
    """Render a compact ASCII snapshot report."""
    lines = [
        "# M20-S1 extraction measurement snapshot",
        "",
        "Ground truth: PyMuPDF page.get_text().",
        "Metric: lowercase word-multiset intersection and difference using token pattern "
        "`(?:\\$[0-9][0-9,]*(?:\\.[0-9]+)?|[a-z0-9%]+)`.",
        "",
        f"- Form PDFs measured: {snapshot['form_count']}",
        f"- Mean shipped-text retention: {snapshot['mean_retention_percent']:.1f}% "
        f"(expected {snapshot['expected_mean_retention_percent']:.1f}%; "
        f"reproduced: {str(snapshot['mean_reproduced']).lower()})",
        "",
        "## Form corpus",
        "",
        "| document | retention | fabrication | producer | pages | widgets | tables |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for item in snapshot["forms"]:
        lines.append(
            f"| {item['document_id']} | {item['retention'] * 100:.1f}% | "
            f"{item['fabrication'] * 100:.1f}% | {item['producer'] or '-'} | "
            f"{item['page_count']} | {item['widget_count']} | "
            f"{item['table_count'] if item['table_count'] is not None else item['table_probe_status']} |"
        )
    lines.extend(["", "## Headline reproduction", ""])
    for document_id, result in snapshot["headline"].items():
        measured = result["measured_percent"]
        measured_text = f"{measured:.1f}%" if measured is not None else "missing"
        lines.append(
            f"- {document_id}: measured {measured_text}, "
            f"expected {result['expected_percent']:.1f}%, reproduced: {str(result['reproduced']).lower()}"
        )
    lines.extend(["", "## Producer-robustness corpus", ""])
    if not snapshot["robustness_corpus"]:
        lines.append("No separate robustness corpus was supplied.")
    else:
        lines.extend(
            [
                "The corpus is test data only. It is not in the acquisition manifest and does not enter graph data.",
                "",
                "| document | producer | text | widgets | structure |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for item in snapshot["robustness_corpus"]:
            layers = item["layers"]
            lines.append(
                f"| {item['document_id']} | {item['producer'] or '-'} | "
                f"{layers['text']['status']} ({layers['text']['word_count']} words) | "
                f"{layers['widgets']['status']} ({layers['widgets']['count']}) | "
                f"{layers['structure']['status']} ({layers['structure']['table_count']}) |"
            )
    return "\n".join(lines) + "\n"


def write_snapshot(snapshot: dict[str, Any], output_dir: str | Path) -> tuple[Path, Path]:
    """Write the machine-readable JSON and the human-readable Markdown snapshot."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "M20_S1_MEASUREMENTS.json"
    markdown_path = output / "M20_S1_MEASUREMENTS.md"
    json_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    markdown_path.write_text(render_snapshot_markdown(snapshot), encoding="utf-8", newline="\n")
    return json_path, markdown_path


def _count_tables(document: Any) -> tuple[int | None, str]:
    count = 0
    for page in document:
        try:
            count += len(page.find_tables().tables)
        except AttributeError:
            return None, "unavailable"
        except Exception as exc:  # pragma: no cover - producer-specific library failures.
            return None, f"error:{type(exc).__name__}"
    return count, "ok"


def _word_counter(text: str) -> Counter[str]:
    return Counter(WORD_TOKEN_RE.findall(text.lower()))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata_value(metadata: dict[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    return str(value) if value else None


def _display_path(path: Path, root: Path | None) -> str:
    resolved = path.resolve()
    if root is not None:
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            pass
    return str(path)
