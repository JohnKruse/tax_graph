"""Local-first document classification for the intake doc drop."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Iterable


SUPPORTED_TYPES = {"w2", "1099_int", "1099_div", "1099_b"}
KNOWN_TYPES = SUPPORTED_TYPES | {"1099_nec", "unknown"}
_BOX_RE = re.compile(r"\bBOX\s+([0-9]+[A-Z]?)\s*[:=]\s*([^\r\n]+)", re.IGNORECASE)


@dataclass(frozen=True)
class DocumentCandidate:
    """One local document presented to the classifier."""

    path: Path
    text: str


@dataclass(frozen=True)
class Classification:
    """Deterministic classification result with evidence and extracted boxes."""

    path: Path
    document_type: str
    confidence: float
    evidence: tuple[str, ...] = ()
    boxes: dict[str, str] = field(default_factory=dict)
    provider: str = "local_rules"

    @property
    def supported(self) -> bool:
        """Whether this document type is in intake v1's bounded set."""
        return self.document_type in SUPPORTED_TYPES


def crawl_documents(drop_dir: str | Path) -> list[DocumentCandidate]:
    """Read text documents from a local drop directory in stable order.

    PDF/OCR integration remains provider-specific; rendered text files are the
    hermetic and keyless intake boundary used by v1.  Binary files are skipped
    with an explicit candidate rather than guessed.
    """
    directory = Path(drop_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"intake drop directory not found: {directory}")
    candidates: list[DocumentCandidate] = []
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = ""
        candidates.append(DocumentCandidate(path=path, text=text))
    return candidates


def classify_document(candidate: DocumentCandidate) -> Classification:
    """Classify one rendered document using transparent local markers."""
    haystack = f"{candidate.path.name}\n{candidate.text}".lower()
    patterns = (
        ("w2", (r"form\s*w-?2", r"wage and tax statement", r"w-?2")),
        ("1099_int", (r"1099\s*-?\s*int", r"interest income")),
        ("1099_div", (r"1099\s*-?\s*div", r"dividends and distributions")),
        ("1099_b", (r"1099\s*-?\s*b", r"proceeds from broker")),
        ("1099_nec", (r"1099\s*-?\s*nec", r"nonemployee compensation")),
    )
    for document_type, candidates in patterns:
        evidence = tuple(pattern for pattern in candidates if re.search(pattern, haystack))
        if evidence:
            boxes = {
                f"box_{label.lower()}": value.strip()
                for label, value in _BOX_RE.findall(candidate.text)
            }
            return Classification(candidate.path, document_type, 1.0, evidence, boxes)
    return Classification(candidate.path, "unknown", 0.0, (), {})


def classify_documents(candidates: Iterable[DocumentCandidate]) -> list[Classification]:
    """Classify candidates in stable path order."""
    return sorted((classify_document(candidate) for candidate in candidates), key=lambda item: str(item.path))
