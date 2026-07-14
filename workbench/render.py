"""Build-time source-PDF rasterization for offline workbench bundles."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Callable


RENDERER_VERSION = "pymupdf-v1"


class PageRenderError(ValueError):
    """Raised when one requested source page cannot be rasterized."""


@dataclass(frozen=True)
class RenderedPage:
    """One page image and its PDF-space dimensions."""

    page_number: int
    path: Path
    width: float
    height: float


PageRenderer = Callable[[Path, int, float], bytes]


class PageImageCache:
    """Content-addressed cache that renders only explicitly requested pages."""

    def __init__(
        self,
        cache_dir: str | Path,
        *,
        renderer: PageRenderer | None = None,
        renderer_version: str = RENDERER_VERSION,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.renderer = renderer or render_pdf_page
        self.renderer_version = renderer_version

    def get(self, pdf_path: Path, pdf_hash: str, page: int, scale: float) -> Path:
        """Return a cached PNG path, rendering one page on a cache miss."""
        if page < 1:
            raise PageRenderError("page numbers are one-based")
        if not 0.5 <= scale <= 4.0:
            raise PageRenderError("scale must be between 0.5 and 4.0")
        key = f"{pdf_hash}:{page}:{scale:.3f}:{self.renderer_version}".encode("ascii")
        name = hashlib.sha256(key).hexdigest() + ".png"
        path = self.cache_dir / name
        if path.is_file():
            return path
        data = self.renderer(pdf_path, page, scale)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)
        return path


def render_pdf_page(pdf_path: Path, page: int, scale: float) -> bytes:
    """Rasterize one one-based PDF page and return PNG bytes."""
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on optional extra.
        raise RuntimeError("PDF rendering needs the optional 'pdf' extra (PyMuPDF)") from exc
    fitz.TOOLS.mupdf_display_errors(False)
    try:
        with fitz.open(str(pdf_path)) as document:
            if page < 1 or page > document.page_count:
                raise PageRenderError(f"page {page} is outside PDF page range 1..{document.page_count}")
            source_page = document.load_page(page - 1)
            pixmap = source_page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            return bytes(pixmap.tobytes("png"))
    except PageRenderError:
        raise
    except Exception as exc:
        raise PageRenderError(f"cannot render {pdf_path.name} page {page}: {exc}") from exc


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
