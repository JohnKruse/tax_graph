"""Build-time source-PDF rasterization for offline workbench bundles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RenderedPage:
    """One page image and its PDF-space dimensions."""

    page_number: int
    path: Path
    width: float
    height: float


def render_pdf_pages(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    dpi: int = 144,
) -> tuple[RenderedPage, ...]:
    """Rasterize all PDF pages to PNGs using the optional build-time extra."""
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on optional extra.
        raise RuntimeError("PDF rendering needs the optional 'pdf' extra (PyMuPDF)") from exc

    # Some IRS-produced PDFs carry malformed accessibility/structure-tree
    # metadata that MuPDF's C layer reports straight to stderr as
    # "format error: No common ancestor in structure tree". This does not
    # affect page rasterization (structure tree is unrelated to visual
    # content) and is not a Python-catchable exception; silence the display
    # of these known-benign warnings without suppressing real errors, which
    # MuPDF still raises as exceptions.
    fitz.TOOLS.mupdf_display_errors(False)

    pdf_file = Path(pdf_path).resolve()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    scale = float(dpi) / 72.0
    matrix = fitz.Matrix(scale, scale)
    pages: list[RenderedPage] = []
    with fitz.open(str(pdf_file)) as document:
        for index, page in enumerate(document):
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image_path = output / f"{pdf_file.stem}_page_{index + 1:03d}.png"
            pixmap.save(str(image_path))
            pages.append(
                RenderedPage(
                    page_number=index + 1,
                    path=image_path,
                    width=float(page.rect.width),
                    height=float(page.rect.height),
                )
            )
    return tuple(pages)
