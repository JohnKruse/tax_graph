"""Provider-free checks for claims made by the extraction pipeline.

The doctor is deliberately a report, not a repair tool.  It turns a small set
of load-bearing plan claims into executable checks and makes missing evidence
visible instead of treating it as an empty result.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as _dt
import inspect
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable

from tax_graph.acquire.manifest import load_manifest
from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.outline import build_outline_tree
from tax_graph.io.loader import load_yaml


BAD_STATUSES = frozenset({"UNKNOWN", "DISAGREES", "STALE"})
_ISO_DATE_RE = re.compile(r"\b(20[0-9]{2}-[0-9]{2}-[0-9]{2})\b")
_TOP_LEVEL_ITEM_RE = re.compile(r"^- (.+)$")
_OPEN_SECTION_RE = re.compile(
    r"^## Open for Architect\s*$([\s\S]*?)(?=^##\s|\Z)",
    re.MULTILINE,
)


@dataclass(frozen=True)
class PlanClaim:
    """Declarative description of one plan claim and its evaluator."""

    claim_id: str
    assertion: str
    predicate: str
    documents: tuple[str, ...] = ()


# Keep this registry small.  A claim belongs here only when a stale value can
# block or misdirect the next pipeline round.
CHECKABLE_CLAIMS = (
    PlanClaim(
        claim_id="m20_s3a_outline_ready",
        assertion="the corrected form outline has semantic children and line anchors",
        predicate="outline_children",
        documents=("form_1040_2025", "schedule_a_2025", "form_2441_2025"),
    ),
)


@dataclass(frozen=True)
class DoctorCheck:
    """One check result shown by the doctor."""

    check_id: str
    status: str
    assertion: str
    message: str
    details: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON/YAML-friendly check record."""
        return {
            "check_id": self.check_id,
            "status": self.status,
            "assertion": self.assertion,
            "message": self.message,
            "details": list(self.details),
        }


@dataclass(frozen=True)
class OperationRow:
    """Cross-layer presence row for one model operation."""

    operation: str
    prompt: bool | None
    validator: bool | None
    projection: bool | None
    engine: bool | None
    detail: str = ""

    @property
    def status(self) -> str:
        """Return the row status without repairing any disagreement."""
        values = (self.prompt, self.validator, self.projection, self.engine)
        if any(value is None for value in values):
            return "UNKNOWN"
        return "HOLDS" if all(values) else "DISAGREES"

    def as_dict(self) -> dict[str, Any]:
        """Return a stable cross-layer record."""
        return {
            "operation": self.operation,
            "prompt": self.prompt,
            "validator": self.validator,
            "projection": self.projection,
            "engine": self.engine,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class OpenItemAge:
    """One handoff item with its git-touch age."""

    title: str
    status: str
    raised_date: str | None
    commits: int | None
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return a stable age record."""
        return {
            "title": self.title,
            "status": self.status,
            "raised_date": self.raised_date,
            "commits": self.commits,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class DoctorReport:
    """Complete result of one provider-free doctor run."""

    year: str
    claims: tuple[DoctorCheck, ...]
    artifacts: tuple[DoctorCheck, ...]
    operations: tuple[OperationRow, ...]
    open_items: tuple[OpenItemAge, ...]

    @property
    def problems(self) -> tuple[str, ...]:
        """Return ids of checks that need attention."""
        problems = [
            item.check_id
            for item in (*self.claims, *self.artifacts)
            if item.status in BAD_STATUSES
        ]
        problems.extend(
            f"operation:{item.operation}"
            for item in self.operations
            if item.status in BAD_STATUSES
        )
        problems.extend(
            f"open-item:{item.title}"
            for item in self.open_items
            if item.status in BAD_STATUSES
        )
        return tuple(problems)

    @property
    def ok(self) -> bool:
        """Return whether the doctor can honestly exit zero."""
        return not self.problems

    def as_dict(self) -> dict[str, Any]:
        """Return a machine-readable report without writing it to disk."""
        return {
            "year": self.year,
            "ok": self.ok,
            "problems": list(self.problems),
            "claims": [item.as_dict() for item in self.claims],
            "artifacts": [item.as_dict() for item in self.artifacts],
            "operations": [item.as_dict() for item in self.operations],
            "open_items": [item.as_dict() for item in self.open_items],
        }


def run_doctor(
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    max_open_item_commits: int = 20,
) -> DoctorReport:
    """Run all doctor checks without providers and without writing artifacts."""
    root_path = Path(root).resolve() if root is not None else project_root()
    year_text = str(year)

    claims = tuple(_run_claim(claim, root_path, year_text) for claim in CHECKABLE_CLAIMS)
    artifacts = _check_declared_artifacts(root_path, year_text)
    operations = _check_operations(root_path)
    open_items = _check_open_item_age(
        root_path,
        max_commits=max_open_item_commits,
    )
    return DoctorReport(
        year=year_text,
        claims=claims,
        artifacts=artifacts,
        operations=operations,
        open_items=open_items,
    )


def render_doctor_report(report: DoctorReport) -> str:
    """Render a short plain-text report suitable for a CI log."""
    lines = [
        "=== doctor ===",
        "provider calls: none",
        "exit 0 means no claim is UNKNOWN, no layer disagrees, and no open item is stale.",
        "",
        "=== executable blockers ===",
    ]
    for item in report.claims:
        lines.append(f"  {item.check_id}: {item.status} - {item.message}")
        lines.append(f"    assertion: {item.assertion}")
        for detail in item.details:
            lines.append(f"    {detail}")

    lines.append("")
    lines.append("=== declared artifacts ===")
    for item in report.artifacts:
        lines.append(f"  {item.check_id}: {item.status} - {item.message}")
        for detail in item.details:
            lines.append(f"    {detail}")

    lines.extend(("", "=== operation vocabulary ==="))
    lines.append("  operation | prompt | validator | projection | engine | status")
    for item in report.operations:
        values = " | ".join(_yes_no(value) for value in (
            item.prompt,
            item.validator,
            item.projection,
            item.engine,
        ))
        lines.append(f"  {item.operation} | {values} | {item.status}")
        if item.detail:
            lines.append(f"    {item.detail}")

    lines.extend(("", "=== open item age ==="))
    if not report.open_items:
        lines.append("  none")
    for item in report.open_items:
        age = "UNKNOWN" if item.commits is None else str(item.commits)
        raised = item.raised_date or "UNKNOWN"
        lines.append(
            f"  {item.status}: age_commits={age}, raised={raised} - {item.title}"
        )
        if item.detail:
            lines.append(f"    {item.detail}")

    if report.ok:
        lines.extend(("", "result: OK", "exit code: 0"))
    else:
        lines.extend(("", "result: NEEDS ATTENTION", "exit code: 1"))
    return "\n".join(lines) + "\n"


def _yes_no(value: bool | None) -> str:
    if value is None:
        return "UNKNOWN"
    return "YES" if value else "NO"


def _run_claim(claim: PlanClaim, root: Path, year: str) -> DoctorCheck:
    predicate = {
        "outline_children": _check_outline_children,
    }.get(claim.predicate)
    if predicate is None:
        return DoctorCheck(
            claim.claim_id,
            "UNKNOWN",
            claim.assertion,
            f"no predicate registered for {claim.predicate}",
        )
    try:
        return predicate(claim, root, year)
    except Exception as exc:
        return DoctorCheck(
            claim.claim_id,
            "UNKNOWN",
            claim.assertion,
            f"predicate failed: {type(exc).__name__}: {exc}",
        )


def _check_outline_children(claim: PlanClaim, root: Path, year: str) -> DoctorCheck:
    details: list[str] = []
    for document_id in claim.documents:
        document = load_document_input(document_id, year=year, root=root)
        outline = build_outline_tree(document)
        nodes = _flatten_outline(outline.children)
        anchors = sum(bool(node.line_anchor) for node in nodes)
        if not nodes:
            return DoctorCheck(
                claim.claim_id,
                "UNKNOWN",
                claim.assertion,
                f"{document_id}: outline produced no children",
                tuple(details),
            )
        details.append(f"{document_id}: {len(nodes)} outline nodes / {anchors} line anchors")
    return DoctorCheck(
        claim.claim_id,
        "CLEARED",
        claim.assertion,
        "all representative documents produced outline children",
        tuple(details),
    )


def _flatten_outline(nodes: Iterable[Any]) -> list[Any]:
    flattened: list[Any] = []
    for node in nodes:
        flattened.append(node)
        flattened.extend(_flatten_outline(node.children))
    return flattened


def _check_declared_artifacts(root: Path, year: str) -> tuple[DoctorCheck, ...]:
    try:
        manifest = load_manifest(root=root)
        config = load_config(root=root)
        raw_store = _configured_path(
            root,
            get_config_value(config, "project.paths.raw_store", ".cache/raw"),
        )
        raw_year = raw_store / year
    except Exception as exc:
        return (
            DoctorCheck(
                "manifest_declared_artifacts",
                "UNKNOWN",
                "every declared source and accepted region has an artifact",
                f"manifest could not be inspected: {type(exc).__name__}: {exc}",
            ),
        )

    checks: list[DoctorCheck] = []
    for entry in manifest.documents:
        if entry.url:
            path = raw_year / f"{entry.document_id}.pdf"
            if path.exists():
                checks.append(
                    DoctorCheck(
                        f"source:{entry.document_id}",
                        "HOLDS",
                        "manifest-declared acquired source exists",
                        "source present",
                        (str(path),),
                    )
                )
            else:
                checks.append(
                    DoctorCheck(
                        f"source:{entry.document_id}",
                        "UNKNOWN",
                        "manifest-declared acquired source exists",
                        "source is missing",
                        (str(path),),
                    )
                )
            continue

        if entry.is_region:
            harvest_path = _find_harvest(root, year, entry.document_id)
            if harvest_path is None:
                checks.append(
                    DoctorCheck(
                        f"harvest:{entry.document_id}",
                        "UNKNOWN",
                        "accepted region has a generated harvest output",
                        "harvest.yaml is missing",
                        tuple(str(path) for path in _harvest_candidates(root, year, entry.document_id)),
                    )
                )
                continue
            try:
                payload = load_yaml(harvest_path) or {}
                if payload.get("document_id") != entry.document_id:
                    raise ValueError(
                        f"document_id is {payload.get('document_id')!r}, expected {entry.document_id!r}"
                    )
            except Exception as exc:
                checks.append(
                    DoctorCheck(
                        f"harvest:{entry.document_id}",
                        "UNKNOWN",
                        "accepted region has a generated harvest output",
                        f"harvest output is invalid: {type(exc).__name__}: {exc}",
                        (str(harvest_path),),
                    )
                )
            else:
                checks.append(
                    DoctorCheck(
                        f"harvest:{entry.document_id}",
                        "HOLDS",
                        "accepted region has a generated harvest output",
                        "harvest present",
                        (str(harvest_path),),
                    )
                )
            continue

        checks.append(
            DoctorCheck(
                f"source:{entry.document_id}",
                "UNKNOWN",
                "every declared source and accepted region has an artifact",
                "manifest entry has neither a source URL nor a region",
            )
        )
    return tuple(checks)


def _configured_path(root: Path, value: Any) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else root / path


def _harvest_candidates(root: Path, year: str, document_id: str) -> tuple[Path, ...]:
    config = load_config(root=root)
    graph_dir = _configured_path(
        root,
        get_config_value(config, "project.paths.graph_dir", "graph"),
    )
    extension_dir = _configured_path(
        root,
        get_config_value(config, "project.paths.graph_ext_dir", "graph_ext"),
    )
    return tuple(
        base / year / "_drafts" / document_id / "harvest.yaml"
        for base in (graph_dir, extension_dir)
    )


def _find_harvest(root: Path, year: str, document_id: str) -> Path | None:
    for path in _harvest_candidates(root, year, document_id):
        try:
            if path.is_file():
                return path
        except OSError:
            continue
    return None


def _check_operations(root: Path) -> tuple[OperationRow, ...]:
    try:
        config = load_config(root=root)
        schema = load_yaml(root / "schemas" / "rule.schema.json")
        operations = [str(item) for item in schema["properties"]["operation"]["enum"]]
        prompt_texts = _load_operation_prompt_texts(root, config)
        from tax_graph.extract.cells import DEFAULT_OPERATIONS, RULE_FOR_OP

        validator_operations = set(DEFAULT_OPERATIONS)
        projectable_operations = set(RULE_FOR_OP) | {"IF_ELSE"}
        engine_source = inspect.getsource(
            __import__("tax_graph.engine.operations", fromlist=["apply_operation"]).apply_operation
        )
        engine_operations = {
            operation
            for operation in operations
            if re.search(rf"operation\s*==\s*['\"]{re.escape(operation)}['\"]", engine_source)
        }
    except Exception as exc:
        return tuple(
            OperationRow(
                operation="<registry>",
                prompt=None,
                validator=None,
                projection=None,
                engine=None,
                detail=(
                    "operation registry could not be inspected: "
                    f"{type(exc).__name__}: {exc}"
                ),
            ),
        )

    rows: list[OperationRow] = []
    for operation in operations:
        prompt = None if prompt_texts is None else any(operation in text for text in prompt_texts)
        validator = operation in validator_operations
        projection = operation in projectable_operations
        engine = operation in engine_operations
        missing = [
            layer
            for layer, present in (
                ("prompt", prompt),
                ("validator", validator),
                ("projection", projection),
                ("engine", engine),
            )
            if present is False
        ]
        rows.append(
            OperationRow(
                operation=operation,
                prompt=prompt,
                validator=validator,
                projection=projection,
                engine=engine,
                detail="missing: " + ", ".join(missing) if missing else "",
            )
        )
    return tuple(rows)


def _load_operation_prompt_texts(root: Path, config: dict[str, Any]) -> tuple[str, ...] | None:
    prompt_config = get_config_value(config, "extraction.prompts", {}) or {}
    paths = (
        prompt_config.get("cells", "prompts/derive_cells.md"),
        prompt_config.get("generator", "prompts/extract_generator.md"),
        prompt_config.get("critic", "prompts/extract_critic.md"),
    )
    texts: list[str] = []
    for value in paths:
        path = Path(str(value))
        if not path.is_absolute():
            path = root / path
        if not path.is_file():
            return None
        texts.append(path.read_text(encoding="utf-8"))
    return tuple(texts)


def _check_open_item_age(root: Path, *, max_commits: int) -> tuple[OpenItemAge, ...]:
    handoff_path = root / "plans" / "AGENT_HANDOFF.md"
    try:
        text = handoff_path.read_text(encoding="ascii")
    except Exception as exc:
        return (
            OpenItemAge(
                "Open for Architect",
                "UNKNOWN",
                None,
                None,
                f"handoff could not be read: {type(exc).__name__}: {exc}",
            ),
        )

    match = _OPEN_SECTION_RE.search(text)
    if match is None:
        return (OpenItemAge("Open for Architect", "UNKNOWN", None, None, "section is missing"),)
    blocks = _top_level_bullets(match.group(1))
    commit_dates, git_error = _handoff_commit_dates(root)
    items: list[OpenItemAge] = []
    for block in blocks:
        first_line = " ".join(block[0].split())
        title = _short_title(first_line)
        closed = bool(re.search(r"\b(?:ANSWERED|CLOSED|WITHDRAWN)\b", first_line))
        raised_match = _ISO_DATE_RE.search(" ".join(block))
        raised_date = raised_match.group(1) if raised_match else None
        if closed:
            items.append(
                OpenItemAge(
                    title,
                    "CLOSED",
                    raised_date,
                    None,
                    "marked closed in the handoff",
                )
            )
            continue
        if raised_date is None or commit_dates is None:
            detail = git_error or "item has no raised date"
            items.append(OpenItemAge(title, "UNKNOWN", raised_date, None, detail))
            continue
        raised = _dt.date.fromisoformat(raised_date)
        age = sum(commit_date >= raised for commit_date in commit_dates)
        status = "STALE" if age > max_commits else "HOLDS"
        detail = f"threshold={max_commits} commits"
        items.append(OpenItemAge(title, status, raised_date, age, detail))
    return tuple(items)


def _top_level_bullets(section: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in section.splitlines():
        if _TOP_LEVEL_ITEM_RE.match(line):
            if current is not None:
                blocks.append(current)
            current = [line[2:].strip()]
        elif current is not None:
            current.append(line.strip())
    if current is not None:
        blocks.append(current)
    return [block for block in blocks if any(block)]


def _short_title(value: str) -> str:
    compact = " ".join(value.split())
    return compact[:180] + ("..." if len(compact) > 180 else "")


def _handoff_commit_dates(root: Path) -> tuple[tuple[_dt.date, ...] | None, str | None]:
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "--format=%ad",
                "--date=short",
                "--",
                "plans/AGENT_HANDOFF.md",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return None, f"git history unavailable: {type(exc).__name__}: {exc}"
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        return None, f"git history unavailable: {detail or 'git log failed'}"
    try:
        dates = tuple(
            _dt.date.fromisoformat(line.strip())
            for line in result.stdout.splitlines()
            if line.strip()
        )
    except ValueError as exc:
        return None, f"git history has an invalid date: {exc}"
    return dates, None


__all__ = [
    "CHECKABLE_CLAIMS",
    "DoctorCheck",
    "DoctorReport",
    "OpenItemAge",
    "OperationRow",
    "PlanClaim",
    "render_doctor_report",
    "run_doctor",
]
