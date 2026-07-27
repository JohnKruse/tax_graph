"""Apply the source-verified M18-S2b citation cleanup to promoted YAML."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import yaml

from tax_graph.acquire.citation_cleanup import derive_clean_quote, infer_source_document_id


_RECORD_RE = re.compile(r"(?m)^- citation_id: .*(?:\n|\Z)")
_FIELD_RE = re.compile(r"^  [a-z_]+:")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    citation_root = root / "graph" / "2025" / "citations"
    raw_root = root / ".cache" / "raw" / "2025"
    available = {path.stem for path in raw_root.glob("*.txt")}
    if not available:
        raise SystemExit("missing acquired 2025 source text")

    before_ids: list[str] = []
    after_ids: list[str] = []
    counts = Counter()
    failures: list[str] = []

    for path in sorted(citation_root.glob("*.yaml")):
        original = path.read_text(encoding="utf-8")
        prefix, records = _split_records(original)
        rewritten: list[str] = []
        for record in records:
            loaded = yaml.safe_load(record)
            citation = loaded[0] if isinstance(loaded, list) else loaded
            citation_id = str(citation["citation_id"])
            before_ids.append(citation_id)
            source_id = infer_source_document_id(citation, available_source_ids=available)
            if source_id is None:
                failures.append(f"{citation_id}: source cannot be determined")
                rewritten.append(record)
                after_ids.append(citation_id)
                continue
            source_text = (raw_root / f"{source_id}.txt").read_text(encoding="utf-8")
            cleanup = derive_clean_quote(citation, source_text)
            if cleanup.reason:
                failures.append(f"{citation_id}: {cleanup.reason}")
            if cleanup.changed:
                counts["quoted_text_changed"] += 1
            if citation.get("source_document_id") is None:
                counts["source_document_id_added"] += 1
            if cleanup.changed or citation.get("source_document_id") is None:
                rewritten.append(
                    _rewrite_record(
                        record,
                        quoted_text=cleanup.quoted_text,
                        source_document_id=source_id,
                        add_source_document_id=citation.get("source_document_id") is None,
                    )
                )
            else:
                rewritten.append(record)
            after_ids.append(citation_id)
        path.write_text(prefix + "".join(rewritten), encoding="utf-8", newline="\n")

    if before_ids != after_ids:
        raise SystemExit("citation IDs changed during cleanup")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"citations={len(before_ids)}")
    print(f"quoted_text_changed={counts['quoted_text_changed']}")
    print(f"source_document_id_added={counts['source_document_id_added']}")
    print("failed_rederivation=0")


def _split_records(text: str) -> tuple[str, list[str]]:
    starts = [match.start() for match in _RECORD_RE.finditer(text)]
    if not starts:
        return text, []
    prefix = text[: starts[0]]
    records = [text[start:end] for start, end in zip(starts, starts[1:] + [len(text)])]
    return prefix, records


def _rewrite_record(
    record: str,
    *,
    quoted_text: str,
    source_document_id: str,
    add_source_document_id: bool,
) -> str:
    lines = record.splitlines(keepends=True)
    if add_source_document_id:
        document_index = next(index for index, line in enumerate(lines) if line.startswith("  document_id:"))
        lines.insert(document_index + 1, f"  source_document_id: {source_document_id}\n")
    quote_index = next(index for index, line in enumerate(lines) if line.startswith("  quoted_text:"))
    end_index = quote_index + 1
    while end_index < len(lines) and not _FIELD_RE.match(lines[end_index]):
        end_index += 1
    rendered = yaml.safe_dump(
        {"quoted_text": quoted_text},
        allow_unicode=False,
        default_flow_style=False,
        sort_keys=False,
    ).splitlines(keepends=True)
    replacement = [f"  {line}" for line in rendered]
    lines[quote_index:end_index] = replacement
    return "".join(lines)


if __name__ == "__main__":
    main()
