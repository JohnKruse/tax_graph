"""Deterministic cross-document printed-line reference resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping

from tax_graph.acquire.manifest import load_manifest
from tax_graph.io.loader import load_yaml


_FORM_KINDS = frozenset({"tax_form", "schedule", "source_document"})
_YEAR_RE = re.compile(r"(?<![0-9])20[0-9]{2}(?![0-9])")
_PAREN_RE = re.compile(r"\(([^()]*)\)")


def _compact(value: str) -> str:
    """Return the comparison spelling used for deterministic aliases."""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _document_base(document_id: str, year: str | int) -> str:
    suffix = f"_{year}"
    return document_id.lower().removesuffix(suffix)


@dataclass(frozen=True)
class FormAliasResolver:
    """Resolve only aliases proven by the maintained source inventories."""

    aliases: Mapping[str, str]
    qualifier_keys: frozenset[str]

    def resolve(self, spelling: str) -> str | None:
        """Return one canonical document id, or ``None`` on an unknown/collision."""
        for key in _alias_keys(spelling, self.qualifier_keys):
            document_id = self.aliases.get(key)
            if document_id is not None:
                return document_id
        return None


def build_form_alias_resolver(
    root: str | Path | None,
    *,
    year: str | int,
) -> FormAliasResolver:
    """Build form aliases from the manifest, SOI labels, and address labels.

    The resolver is intentionally fail-closed: aliases that would identify more
    than one modelled document are removed instead of being guessed.
    """
    root_path = Path(root).resolve() if root is not None else Path.cwd().resolve()
    modelled_ids: set[str] = set()
    try:
        manifest = load_manifest(root=root_path)
    except (FileNotFoundError, KeyError, ValueError):
        manifest = None
    if manifest is not None:
        modelled_ids = {
            entry.document_id
            for entry in manifest.documents
            if entry.kind in _FORM_KINDS and not entry.is_region
        }

    raw_by_document: dict[str, set[str]] = {document_id: {document_id} for document_id in modelled_ids}
    for document_id in modelled_ids:
        raw_by_document[document_id].add(_document_base(document_id, year))

    soi_path = root_path / "data" / "soi" / "form_id_map.yaml"
    if soi_path.exists():
        soi_data = load_yaml(soi_path) or {}
        for label, record in (soi_data.get("labels") or {}).items():
            target = str((record or {}).get("document_id") or "")
            if target in raw_by_document:
                raw_by_document[target].add(str(label))

    address_root = root_path / "graph" / str(year) / "addresses"
    for document_id in modelled_ids:
        address_path = address_root / f"{document_id}.yaml"
        if not address_path.exists():
            continue
        data = load_yaml(address_path) or {}
        for address in data.get("addresses") or []:
            if address.get("kind") != "document":
                continue
            for value in [address.get("printed_label"), *(address.get("aliases") or [])]:
                if value:
                    raw_by_document[document_id].add(str(value))

    qualifier_keys = frozenset(
        _compact(str(label))
        for label, record in _soi_labels(soi_path)
        if str((record or {}).get("document_id") or "").strip()
    )
    candidates: dict[str, set[str]] = {}
    for document_id, raw_values in raw_by_document.items():
        for raw_value in raw_values:
            for key in _alias_keys(raw_value, qualifier_keys):
                candidates.setdefault(key, set()).add(document_id)
    aliases = {
        key: next(iter(document_ids))
        for key, document_ids in candidates.items()
        if len(document_ids) == 1
    }
    return FormAliasResolver(aliases=aliases, qualifier_keys=qualifier_keys)


def build_modelled_line_index(
    root: str | Path | None,
    *,
    year: str | int,
    current_document_id: str,
    current_nodes: list[Any],
    resolver: FormAliasResolver | None = None,
) -> dict[tuple[str, str], str]:
    """Index current and already modelled documents by canonical line key."""
    root_path = Path(root).resolve() if root is not None else Path.cwd().resolve()
    active_resolver = resolver or build_form_alias_resolver(root_path, year=year)
    index = outline_line_index(current_document_id, current_nodes)
    for document_id in sorted(set(active_resolver.aliases.values())):
        if document_id == current_document_id:
            continue
        # The address inventory is the machine-readable proof that a document
        # is in the promoted modelled set.  Manifest-only frontier forms (for
        # example Form 2441) remain explicit external identities and must not
        # become guessed graph edges from a draft outline.
        address_path = root_path / "graph" / str(year) / "addresses" / f"{document_id}.yaml"
        if not address_path.exists():
            continue
        outline_path = (
            root_path
            / "graph"
            / str(year)
            / "_drafts"
            / document_id
            / "outline.yaml"
        )
        if not outline_path.exists():
            continue
        data = load_yaml(outline_path) or {}
        other = outline_line_index(document_id, data.get("children") or [])
        _merge_unambiguous(index, other)
    return index


def outline_line_index(document_id: str, nodes: list[Any]) -> dict[tuple[str, str], str]:
    """Build a collision-safe line index from OutlineNodes or YAML mappings."""
    index: dict[tuple[str, str], str] = {}
    ambiguous: set[tuple[str, str]] = set()

    def visit(items: list[Any]) -> None:
        for item in items:
            if isinstance(item, Mapping):
                anchor = str(item.get("line_anchor") or "").strip().lower()
                outline_id = str(item.get("outline_id") or "").strip()
                children = item.get("children") or []
            else:
                anchor = str(getattr(item, "line_anchor", "") or "").strip().lower()
                outline_id = str(getattr(item, "outline_id", "") or "").strip()
                children = getattr(item, "children", []) or []
            if anchor and outline_id:
                value = re.sub(
                    r"[^a-z0-9]+",
                    "_",
                    f"{document_id}_{outline_id}".lower(),
                ).strip("_")
                key = (document_id.lower(), anchor)
                if key in index and index[key] != value:
                    ambiguous.add(key)
                else:
                    index[key] = value
            visit(list(children))

    visit(list(nodes))
    for key in ambiguous:
        index.pop(key, None)
    return index


def _merge_unambiguous(
    destination: dict[tuple[str, str], str],
    source: Mapping[tuple[str, str], str],
) -> None:
    """Merge an index without allowing duplicate line identities to guess."""
    for key, value in source.items():
        if key in destination and destination[key] != value:
            destination.pop(key, None)
        elif key not in destination:
            destination[key] = value


def _soi_labels(path: Path) -> list[tuple[str, Any]]:
    if not path.exists():
        return []
    data = load_yaml(path) or {}
    return [(str(label), record) for label, record in (data.get("labels") or {}).items()]


def _alias_keys(value: str, qualifier_keys: frozenset[str]) -> set[str]:
    """Return source-derived spelling variants, never fuzzy candidates."""
    raw = str(value).strip()
    keys = {_compact(raw)}
    without_year = _YEAR_RE.sub(" ", raw)
    keys.add(_compact(without_year))
    parenthesized = list(_PAREN_RE.finditer(raw))
    if parenthesized and all(
        _compact(match.group(1)) in qualifier_keys
        or _YEAR_RE.fullmatch(match.group(1).strip())
        for match in parenthesized
    ):
        without_qualifiers = _PAREN_RE.sub(" ", raw)
        keys.add(_compact(without_qualifiers))
        keys.add(_compact(_YEAR_RE.sub(" ", without_qualifiers)))
    for key in list(keys):
        if key.startswith("form") and len(key) > len("form"):
            keys.add(key[len("form"):])
    return {key for key in keys if key}
