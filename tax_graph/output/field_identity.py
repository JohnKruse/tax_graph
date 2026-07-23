"""Resolve AcroForm field identity from structure and printed captions.

This module is deliberately read-only. It produces identity observations for a
field inventory; it does not write field maps, bindings, or graph artifacts.
The resolver gives qualified field-name structure precedence over a mined line
anchor. A printed caption is used only as adjacent evidence for the line and
control role, never as an unconstrained label search.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, Mapping, Sequence


_SEGMENT_RE = re.compile(r"^(?P<name>[^\[]+)(?:\[(?P<index>\d+)\])?$")
_LINE_RE = re.compile(r"^Line(?P<line>[0-9]+[a-z]?)(?:_ReadOrder)?$", re.IGNORECASE)
_TABLE_LINE_RE = re.compile(r"^Table_Line(?P<line>[0-9]+[a-z]?)(?:_Part\d+)?$", re.IGNORECASE)
_BOX_RE = re.compile(r"^Box(?:es)?(?P<box>[A-Za-z0-9]+)(?:_ReadOrder)?$", re.IGNORECASE)
_CAPTION_RE = re.compile(r"^\s*-\s*(?P<ref>[0-9]+[a-z]?|[a-z]):\s*(?P<text>.*)$", re.IGNORECASE)
_PRINTED_LINE_RE = re.compile(r"\bline\s+(?P<line>[0-9]+[a-z]?)\b", re.IGNORECASE)
_PRINTED_BOX_RE = re.compile(r"\bbox\s+(?P<box>[0-9]+[a-z]?)\b", re.IGNORECASE)


@dataclass(frozen=True)
class FieldStructure:
    """Parsed qualified-name evidence for one terminal AcroForm control."""

    segments: tuple[str, ...]
    explicit_line: str | None
    box: str | None
    table: str | None
    copy: str | None


@dataclass(frozen=True)
class FieldIdentity:
    """Read-only identity result for one AcroForm control.

    ``line`` is a printed line token for line controls. For controls whose
    structure is a numbered box, it is ``box:<token>`` so the result remains a
    stable field identity while callers can still distinguish it from a line.
    ``role`` is a canonical control role such as ``amount`` or ``checkbox``.
    ``status`` is ``resolved`` only when both components are established.
    """

    field_name: str
    line: str | None
    role: str | None
    status: str
    evidence: tuple[str, ...]
    official_ref: str | None = None
    caption: str = ""

    @property
    def identity(self) -> tuple[str | None, str | None]:
        """Return the comparison-friendly ``(line, role)`` tuple."""
        return self.line, self.role


@dataclass(frozen=True)
class CorpusComparison:
    """Aggregate comparison of derived identities against authored records."""

    document_id: str
    total: int
    agreement: int
    disagreement: int
    unresolved: int
    examples: tuple[str, ...]


def parse_field_structure(field_name: str) -> FieldStructure:
    """Parse qualified wrappers without interpreting terminal numeric suffixes."""
    segments = tuple(_segment_name(part) for part in str(field_name).split(".") if part)
    explicit_line: str | None = None
    box: str | None = None
    table: str | None = None
    copy: str | None = None
    for segment in segments:
        line_match = _LINE_RE.fullmatch(segment) or _TABLE_LINE_RE.fullmatch(segment)
        if line_match:
            explicit_line = _canonical_line(line_match.group("line"))
        box_match = _BOX_RE.fullmatch(segment)
        if box_match:
            box = box_match.group("box").lower()
        if segment.lower().startswith("table_"):
            table = segment
        if segment.lower().startswith("copy"):
            copy = segment
    return FieldStructure(segments, explicit_line, box, table, copy)


def resolve_field(
    field: Mapping[str, Any],
    *,
    fields: Sequence[Mapping[str, Any]] = (),
    rendered_text: str | Sequence[str] | None = None,
) -> FieldIdentity:
    """Resolve one field from qualified structure, row structure, and captions.

    ``fields`` is the complete page/document inventory when same-row structural
    inheritance is needed. Passing it is what resolves Schedule 2's ``f1_15``:
    its raw anchor says ``1``, but it shares a row with the qualified
    ``Line4_ReadOrder`` group, which is stronger evidence for line 4.
    """
    field_name = str(field.get("field_name", "<unnamed>"))
    structure = parse_field_structure(field_name)
    captions = _caption_index(rendered_text)
    caption = _caption_for(field, structure, captions)
    evidence: list[str] = []

    if structure.explicit_line is not None:
        line = structure.explicit_line
        evidence.append("qualified line wrapper")
    elif structure.box is not None:
        line = f"box:{structure.box}"
        evidence.append("qualified box wrapper")
    else:
        line = _same_row_structural_line(field, fields)
        if line is not None:
            evidence.append("same-row qualified wrapper")
        else:
            line = _anchor_line(field.get("line_anchor"), caption)
            if line is not None:
                evidence.append("printed line anchor")
            else:
                line = _caption_line(caption)
                if line is not None:
                    evidence.append("adjacent printed caption")

    role = _control_role(field, caption, structure)
    if role is not None:
        evidence.append("control metadata" if _field_kind(field) != "Text" else "caption/control role")
    status = "resolved" if line is not None and role is not None else "unresolved"
    if status == "unresolved":
        evidence.append("insufficient non-guessing evidence")
    official_ref = line.removeprefix("box:") if line and line.startswith("box:") else line
    return FieldIdentity(
        field_name=field_name,
        line=line,
        role=role,
        status=status,
        evidence=tuple(evidence),
        official_ref=official_ref,
        caption=caption,
    )


def resolve_fields(
    fields: Iterable[Mapping[str, Any]],
    *,
    rendered_text: str | Sequence[str] | None = None,
) -> tuple[FieldIdentity, ...]:
    """Resolve an inventory in stable input order using shared row evidence."""
    inventory = tuple(fields)
    return tuple(resolve_field(item, fields=inventory, rendered_text=rendered_text) for item in inventory)


def compare_identities(
    document_id: str,
    derived: Iterable[FieldIdentity],
    authored: Mapping[str, tuple[str | None, str | None]],
    *,
    max_examples: int = 5,
) -> CorpusComparison:
    """Compare resolver output with an authored field-to-identity projection.

    Missing authored entries and unresolved resolver results are reported as
    unresolved. A disagreement is retained as a finding; this function never
    changes either side.
    """
    agreement = disagreement = unresolved = 0
    examples: list[str] = []
    results = tuple(derived)
    for item in results:
        expected = authored.get(item.field_name)
        if item.status != "resolved" or expected is None:
            unresolved += 1
            if len(examples) < max_examples:
                examples.append(f"unresolved: {item.field_name} -> derived={item.identity!r} expected={expected!r}")
        elif item.identity == expected:
            agreement += 1
        else:
            disagreement += 1
            if len(examples) < max_examples:
                examples.append(f"disagreement: {item.field_name} -> derived={item.identity!r} expected={expected!r}")
    return CorpusComparison(document_id, len(results), agreement, disagreement, unresolved, tuple(examples))


def _segment_name(value: str) -> str:
    match = _SEGMENT_RE.fullmatch(value)
    return match.group("name") if match else value


def _canonical_line(value: str) -> str:
    token = value.lower()
    return "1z" if token == "z" else token


def _field_kind(field: Mapping[str, Any]) -> str:
    explicit = str(field.get("field_type", ""))
    if explicit:
        return explicit
    name = str(field.get("field_name", "")).rsplit(".", 1)[-1].lower()
    if name.startswith("c"):
        return "CheckBox"
    if name.startswith("r"):
        return "RadioButton"
    return "Text" if name.startswith("f") else ""


def _control_role(
    field: Mapping[str, Any], caption: str, structure: FieldStructure
) -> str | None:
    kind = _field_kind(field).lower()
    if kind in {"checkbox", "checkboxes"} or kind == "checkbox":
        return "checkbox"
    if kind in {"radiobutton", "radio"}:
        return "radio"
    if kind == "choice":
        return "choice"
    if kind == "signature":
        return "signature"
    lowered = caption.lower()
    if any(token in lowered for token in ("date", "dob", "acquired", "sold or disposed")):
        return "date"
    if any(token in lowered for token in ("ssn", "social security", "taxpayer identification", "tin", "identification no")):
        return "identifier"
    if any(token in lowered for token in ("description", "name", "address", "city", "state", "country", "zip")):
        return "description" if "description" in lowered else "text"
    if any(token in lowered for token in (
        "amount", "income", "tax", "wages", "proceeds", "basis", "gain", "loss",
        "dividend", "interest", "deduction", "contribution", "withheld", "expenses",
    )):
        return "amount"
    if structure.explicit_line is not None or field.get("line_anchor") is not None:
        return "amount"
    return None


def _anchor_line(value: Any, caption: str) -> str | None:
    if value is None:
        return None
    token = str(value).strip().lower()
    if re.fullmatch(r"[0-9]+[a-z]?", token):
        return _canonical_line(token)
    if token == "z":
        return "1z"
    caption_line = _caption_line(caption)
    return caption_line


def _caption_index(rendered_text: str | Sequence[str] | None) -> tuple[tuple[str, str], ...]:
    if rendered_text is None:
        return ()
    lines = rendered_text.splitlines() if isinstance(rendered_text, str) else tuple(str(item) for item in rendered_text)
    captions: list[tuple[str, str]] = []
    for line in lines:
        match = _CAPTION_RE.match(line)
        if match:
            captions.append((_canonical_line(match.group("ref")), match.group("text").strip()))
    return tuple(captions)


def _caption_for(
    field: Mapping[str, Any], structure: FieldStructure, captions: Sequence[tuple[str, str]]
) -> str:
    if not captions:
        return ""
    anchor = str(field.get("line_anchor", "")).lower()
    if anchor == "z":
        anchor = "1z"
    for ref, text in captions:
        if anchor and ref == anchor:
            return text
    if structure.explicit_line:
        for ref, text in captions:
            if ref == structure.explicit_line:
                return text
    return ""


def _caption_line(caption: str) -> str | None:
    if not caption:
        return None
    match = _PRINTED_LINE_RE.search(caption)
    return _canonical_line(match.group("line")) if match else None


def _same_row_structural_line(
    field: Mapping[str, Any], fields: Sequence[Mapping[str, Any]], tolerance: float = 6.0
) -> str | None:
    page = field.get("page")
    y0 = field.get("y0")
    if page is None or y0 is None:
        return None
    candidates: set[str] = set()
    for other in fields:
        if other is field or other.get("page") != page or other.get("y0") is None:
            continue
        if abs(float(other["y0"]) - float(y0)) > tolerance:
            continue
        structure = parse_field_structure(str(other.get("field_name", "")))
        if structure.explicit_line is not None:
            candidates.add(structure.explicit_line)
    return next(iter(candidates)) if len(candidates) == 1 else None
