"""Static, offline HTML bundle generation for review artifacts."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from workbench.artifacts import ArtifactBundle, load_artifact_bundle
from workbench.geometry import GeometryIndex
from workbench.manifest import build_manifest
from workbench.render import RenderedPage, render_pdf_pages


def build_bundle(
    root: str | Path,
    year: str | int,
    *,
    output_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    pdf_dir: str | Path | None = None,
) -> Path:
    """Build a self-contained static review bundle and return its index path."""
    root_path = Path(root).resolve()
    output = Path(output_dir) if output_dir is not None else root_path / "output" / "review-workbench" / str(year)
    output.mkdir(parents=True, exist_ok=True)
    bundle = load_artifact_bundle(root_path, year, db_path=db_path, pdf_dir=pdf_dir)
    manifest = build_manifest(root_path, year, db_path=db_path, pdf_dir=pdf_dir)
    pages_root = output / "pages"
    rendered: dict[str, tuple[RenderedPage, ...]] = {}
    for pdf in bundle.pdfs:
        rendered[pdf.path.stem] = render_pdf_pages(pdf.path, pages_root)

    document = _build_document(bundle, rendered, output, manifest)
    index_path = output / "index.html"
    index_path.write_text(document, encoding="utf-8", newline="\n")
    return index_path


def _build_document(
    bundle: ArtifactBundle,
    rendered: dict[str, tuple[RenderedPage, ...]],
    output: Path,
    manifest: dict[str, Any],
) -> str:
    index = GeometryIndex(bundle.geometry)
    known_nodes = {str(item.get("node_id")) for item in bundle.graph.objects("nodes")}
    pages: list[str] = []
    for pdf_stem, page_list in sorted(rendered.items()):
        document_id = pdf_stem
        for page in page_list:
            entries = [
                entry
                for entry in index.field_entries
                if entry.get("document_id") == document_id and int(entry.get("page", -1)) == page.page_number
            ]
            overlays = "\n".join(_overlay(entry, known_nodes=known_nodes) for entry in entries)
            image = page.path.relative_to(output).as_posix()
            pages.append(
                '<section class="form-page" data-document="{doc}" data-page="{page}" '
                'style="--page-width:{width}px;--page-height:{height}px">'
                '<h2>{doc} page {page}</h2><div class="page-canvas">'
                '<img src="{image}" alt="{doc} page {page}">'
                '<svg viewBox="0 0 {width} {height}" aria-label="geometry overlays">{overlays}</svg>'
                '</div></section>'.format(
                    doc=html.escape(document_id, quote=True),
                    page=page.page_number,
                    width=_number(page.width),
                    height=_number(page.height),
                    image=html.escape(image, quote=True),
                    overlays=overlays,
                )
            )
    payload = {
        "tax_year": bundle.tax_year,
        "geometry": bundle.geometry,
        "manifest": manifest,
        "graph": {
            kind: list(bundle.graph.objects(kind))
            for kind in ("nodes", "rules", "edges", "citations", "decisions")
        },
        "metrics": bundle.metrics,
        "nversion": bundle.nversion_reports,
        "mined_examples": bundle.mined_examples,
    }
    data = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).replace("<", "\\u003c")
    template = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tax Graph review workbench - __YEAR__</title>
<style>
body {{ margin: 0; font: 14px sans-serif; color: #202124; background: #f4f5f7; }}
header {{ padding: 12px 18px; background: #16202a; color: white; position: sticky; top: 0; z-index: 5; }}
main {{ display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 16px; padding: 16px; }}
.form-page {{ margin: 0 auto 20px; max-width: 900px; background: white; padding: 8px; box-shadow: 0 1px 4px #999; }}
.form-page h2 {{ font-size: 14px; margin: 2px 0 8px; }}
.page-canvas {{ position: relative; width: 100%; }}
.page-canvas img {{ display: block; width: 100%; height: auto; }}
.page-canvas svg {{ position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }}
svg rect {{ pointer-events: all; cursor: pointer; fill-opacity: .04; stroke-width: 1.2; }}
svg .field {{ stroke: #2878c8; }} svg .provenance {{ stroke: #d44a2c; fill: #d44a2c; }}
svg .gap {{ stroke: #c48a00; stroke-dasharray: 3 2; }}
aside {{ position: sticky; top: 62px; align-self: start; background: white; padding: 14px; min-height: 180px; box-shadow: 0 1px 4px #bbb; overflow-wrap: anywhere; }}
.finding {{ border-left: 4px solid #c48a00; padding: 6px; background: #fff8dc; }}
pre {{ white-space: pre-wrap; font-size: 12px; }}
</style>
</head>
<body><header><strong>Tax Graph review workbench</strong> - tax year __YEAR__</header>
<main><div id="pages">__PAGES__</div><aside id="panel"><h2>Inspect a form region</h2>
<p>Click a blue field or red resolved-provenance anchor. Yellow dashed regions are visible gaps.</p></aside></main>
<script id="artifact-data" type="application/json">__DATA__</script>
<script>
const ARTIFACTS = JSON.parse(document.getElementById("artifact-data").textContent);
const panel = document.getElementById("panel");
function esc(value) {{ const node = document.createElement("span"); node.textContent = String(value ?? ""); return node.innerHTML; }}
function inspect(entry, layer) {{
  const nodeId = entry.node_id;
  const node = (ARTIFACTS.graph.nodes || []).find(item => item.node_id === nodeId);
  const reviewItems = (ARTIFACTS.manifest.entries || []).flatMap(item => (item.units || []).filter(unit =>
    (unit.object_refs || []).some(ref => ref.object_type === "node" && ref.object_id === nodeId) ||
    (unit.official_location || {}).document_id === entry.document_id
  ));
  const gaps = !nodeId || entry.unresolvable;
  panel.innerHTML = gaps ? `<h2>Unresolved form region</h2><div class="finding">${esc(entry.identity_slot || entry.slot)} is visible as a finding; no static node is claimed.</div>` :
    `<h2>${esc(nodeId)}</h2><p>Layer: ${esc(layer)}</p><p>${esc(node && (node.label || node.node_type) || "node not present in compiled graph")}</p>`;
  const detail = { entry, node, review_items: reviewItems };
  panel.insertAdjacentHTML("beforeend", `<pre>${esc(JSON.stringify(detail, null, 2))}</pre>`);
}}
document.querySelectorAll("svg rect").forEach(rect => rect.addEventListener("click", event => {{
  event.stopPropagation(); inspect(JSON.parse(rect.dataset.entry), rect.dataset.layer);
}}));
</script></body></html>
"""
    return (
        template.replace("__YEAR__", str(bundle.tax_year))
        .replace("__PAGES__", "\n".join(pages))
        .replace("__DATA__", data)
    )


def _overlay(entry: dict[str, Any], *, known_nodes: set[str]) -> str:
    rect = entry["rect"]
    node_id = entry.get("node_id")
    display_entry = dict(entry)
    display_entry["unresolvable"] = bool(node_id and str(node_id) not in known_nodes)
    layer = "provenance" if node_id and not display_entry["unresolvable"] else "gap"
    data = json.dumps(display_entry, ensure_ascii=True, sort_keys=True, separators=(",", ":")).replace("&", "&amp;").replace('"', "&quot;")
    return '<rect class="{layer}" x="{x}" y="{y}" width="{w}" height="{h}" data-layer="{layer}" data-entry="{data}" />'.format(
        layer=layer,
        x=_number(float(rect[0])),
        y=_number(float(rect[1])),
        w=_number(float(rect[2]) - float(rect[0])),
        h=_number(float(rect[3]) - float(rect[1])),
        data=data,
    )


def _number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".") or "0"
