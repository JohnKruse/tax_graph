"""Phase step driver for tiered worker-session orchestration.

The driver reads a phase plan, extracts step tier tags, renders one command per
step from ``config/driver.yaml``, and runs gate commands between steps. It
always stops before a step marked as John's gate.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from tax_graph.config import project_root


DEFAULT_DRIVER_CONFIG = "config/driver.yaml"
STEP_HEADER_RE = re.compile(
    r"^- \[(?P<box>[ xX])\] \*\*Step (?P<number>\d+) "
    r"\[(?P<tier>[a-z-]+)\] - (?P<title>.+?)\.\*\*(?P<body>.*?)(?=^- \[[ xX]\] \*\*Step |\Z)"
    ,
    re.MULTILINE | re.DOTALL,
)
PHASE_HEADER_RE = re.compile(r"^# PHASE (?P<phase_id>M\d+[a-z]?) - (?P<title>.+?)\s+\[(?P<status>.)\]")
CANARY_RE = re.compile(r"^\*\*Canary:\*\* (?P<canary>.+)$")


@dataclass(frozen=True)
class DriverStep:
    """A parsed phase-plan step."""

    number: int
    tier: str
    title: str
    body: str
    checked: bool
    john_gate: bool


@dataclass(frozen=True)
class PhasePlan:
    """Parsed phase metadata plus ordered steps."""

    phase_id: str
    title: str
    canary: str
    steps: tuple[DriverStep, ...]
    path: Path


@dataclass(frozen=True)
class GateCommand:
    """A named gate command executed between steps."""

    name: str
    command_template: tuple[str, ...]


@dataclass(frozen=True)
class TierCommand:
    """A tier-mapped worker launcher template."""

    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class DriverConfig:
    """Resolved driver configuration."""

    tiers: dict[str, TierCommand]
    gates: tuple[GateCommand, ...]


@dataclass(frozen=True)
class DriverRunResult:
    """Outcome summary for one driver invocation."""

    exit_code: int
    stopped_before_step: int | None = None
    gate_failure: str | None = None


def load_driver_config(path: str | Path | None = None, *, root: str | Path | None = None) -> DriverConfig:
    """Load and validate the step-driver config."""
    root_path = Path(root).resolve() if root is not None else project_root()
    config_path = Path(path) if path is not None else root_path / DEFAULT_DRIVER_CONFIG
    if not config_path.is_absolute():
        config_path = root_path / config_path
    if not config_path.exists():
        raise FileNotFoundError(f"driver config not found: {config_path}")

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    tiers_payload = payload.get("tiers")
    if not isinstance(tiers_payload, dict) or not tiers_payload:
        raise ValueError("driver config must define a non-empty 'tiers' mapping")

    gates_payload = payload.get("gates")
    if not isinstance(gates_payload, list) or not gates_payload:
        raise ValueError("driver config must define a non-empty 'gates' list")

    tiers: dict[str, TierCommand] = {}
    for tier_name, tier_spec in tiers_payload.items():
        if not isinstance(tier_spec, dict):
            raise ValueError(f"tier '{tier_name}' must be a mapping")
        command = _coerce_command_list(tier_spec.get("command"), label=f"tier '{tier_name}' command")
        tiers[str(tier_name)] = TierCommand(name=str(tier_name), command=tuple(command))

    gates: list[GateCommand] = []
    for index, gate_spec in enumerate(gates_payload, start=1):
        if not isinstance(gate_spec, dict):
            raise ValueError(f"gate #{index} must be a mapping")
        name = str(gate_spec.get("name") or f"gate-{index}")
        command = _coerce_command_list(gate_spec.get("command"), label=f"gate '{name}' command")
        gates.append(GateCommand(name=name, command_template=tuple(command)))

    return DriverConfig(tiers=tiers, gates=tuple(gates))


def parse_phase_plan(plan_path: str | Path) -> PhasePlan:
    """Parse the phase markdown file for step metadata."""
    path = Path(plan_path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    phase_id = ""
    title = ""
    canary = ""
    steps: list[DriverStep] = []

    for line in lines:
        if not phase_id:
            match = PHASE_HEADER_RE.match(line)
            if match:
                phase_id = match.group("phase_id")
                title = match.group("title").strip()
                continue
        if not canary:
            match = CANARY_RE.match(line)
            if match:
                canary = match.group("canary").strip()
                break

    for match in STEP_HEADER_RE.finditer(text):
        raw_title = match.group("title")
        title_text = " ".join(raw_title.split())
        body_text = match.group("body").strip()
        title_lower = title_text.lower()
        body_first_line = body_text.splitlines()[0].strip().lower() if body_text else ""
        steps.append(
            DriverStep(
                number=int(match.group("number")),
                tier=match.group("tier"),
                title=title_text,
                body=body_text,
                checked=match.group("box").lower() == "x",
                john_gate=(
                    "john's gate" in title_lower
                    or "john's gates" in title_lower
                    or "driver stops here" in body_first_line
                    or "driver stops here" in title_lower
                ),
            )
        )

    if not phase_id or not canary:
        raise ValueError(f"could not parse phase metadata from {path}")
    if not steps:
        raise ValueError(f"no steps found in {path}")

    return PhasePlan(
        phase_id=phase_id,
        title=title,
        canary=canary,
        steps=tuple(steps),
        path=path.resolve(),
    )


def run_driver(
    *,
    plan: PhasePlan,
    config: DriverConfig,
    root: str | Path | None = None,
    dry_run: bool = False,
    stdout: Any = None,
    stderr: Any = None,
) -> DriverRunResult:
    """Run the parsed step plan."""
    root_path = Path(root).resolve() if root is not None else project_root()
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    _print_plan_header(plan, out)

    executable_steps = [step for step in plan.steps if not step.checked]
    if not executable_steps:
        print("No incomplete steps found.", file=out)
        return DriverRunResult(exit_code=0)

    for index, step in enumerate(executable_steps):
        if step.john_gate:
            print(
                f"STOP: Step {step.number} is marked as John's gate; hand off before launching it.",
                file=out,
            )
            return DriverRunResult(exit_code=0, stopped_before_step=step.number)

        tier_command = config.tiers.get(step.tier)
        if tier_command is None:
            raise ValueError(f"no driver tier mapping configured for '{step.tier}'")

        prompt_text = build_step_prompt(plan, step)
        with tempfile.TemporaryDirectory(prefix="tax-graph-step-driver-") as temp_dir:
            prompt_path = Path(temp_dir) / f"{plan.phase_id.lower()}_step_{step.number:02d}.txt"
            prompt_path.write_text(prompt_text, encoding="utf-8", newline="\n")
            command = render_command(
                tier_command.command,
                {
                    "phase_id": plan.phase_id,
                    "phase_title": plan.title,
                    "phase_path": str(plan.path),
                    "canary": plan.canary,
                    "step_number": str(step.number),
                    "step_tier": step.tier,
                    "step_title": step.title,
                    "step_body": step.body,
                    "prompt": prompt_text,
                    "prompt_file": str(prompt_path),
                    "root": str(root_path),
                },
            )
            print(
                f"Step {step.number} [{step.tier}] -> {' '.join(command)}",
                file=out,
            )
            if dry_run:
                continue
            result = subprocess.run(command, cwd=root_path, text=True, check=False)
            if result.returncode != 0:
                print(
                    f"Step {step.number} failed with exit code {result.returncode}.",
                    file=err,
                )
                return DriverRunResult(exit_code=result.returncode)

        if index == len(executable_steps) - 1:
            continue
        gate_result = run_gates(config.gates, root=root_path, dry_run=dry_run, stdout=out, stderr=err)
        if gate_result.exit_code != 0:
            return gate_result

    return DriverRunResult(exit_code=0)


def run_gates(
    gates: tuple[GateCommand, ...],
    *,
    root: str | Path,
    dry_run: bool = False,
    stdout: Any = None,
    stderr: Any = None,
) -> DriverRunResult:
    """Run the configured gate suite."""
    root_path = Path(root).resolve()
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    print("Running gate suite before the next step.", file=out)
    for gate in gates:
        command = render_command(gate.command_template, {"root": str(root_path)})
        print(f"  gate {gate.name}: {' '.join(command)}", file=out)
        if dry_run:
            continue
        result = subprocess.run(command, cwd=root_path, text=True, check=False)
        if result.returncode != 0:
            print(
                f"Gate '{gate.name}' failed with exit code {result.returncode}; blocking the next step.",
                file=err,
            )
            return DriverRunResult(exit_code=result.returncode, gate_failure=gate.name)
    return DriverRunResult(exit_code=0)


def build_step_prompt(plan: PhasePlan, step: DriverStep) -> str:
    """Build the worker prompt for one launched session."""
    body = step.body.strip() or "(no additional step body)"
    return (
        f"Phase {plan.phase_id}: {plan.title}\n"
        f"Canary: {plan.canary}\n"
        f"Plan file: {plan.path}\n"
        f"Step {step.number} [{step.tier}]: {step.title}\n\n"
        f"{body}\n\n"
        "Work only this step. Follow AGENTS.md, the phase plan, and the shared handoff. "
        "Implement code, tests, and docs required by the step, and stop if you hit a real blocker."
    )


def render_command(command_template: tuple[str, ...], context: dict[str, str]) -> list[str]:
    """Render a configured command template with step context."""
    return [part.format(**context) for part in command_template]


def resolve_plan_path(
    *,
    phase: str | None = None,
    plan: str | Path | None = None,
    root: str | Path | None = None,
) -> Path:
    """Resolve a phase id or explicit plan path to a markdown file."""
    root_path = Path(root).resolve() if root is not None else project_root()
    if plan is not None:
        resolved = Path(plan)
        if not resolved.is_absolute():
            resolved = root_path / resolved
        return resolved.resolve()
    if phase is None:
        raise ValueError("provide either --phase or --plan")
    return (root_path / "plans" / f"PHASE_{phase.upper()}.md").resolve()


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the standalone step-driver script."""
    parser = argparse.ArgumentParser(description="Run tiered worker sessions from a phase plan.")
    parser.add_argument("--phase", help="Phase id, for example M10.")
    parser.add_argument("--plan", help="Explicit phase markdown path.")
    parser.add_argument("--config", default=DEFAULT_DRIVER_CONFIG, help="Driver config YAML path.")
    parser.add_argument("--root", default=None, help="Project root override.")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned sequence without launching.")
    args = parser.parse_args(argv)

    try:
        root_path = Path(args.root).resolve() if args.root is not None else project_root()
        plan_path = resolve_plan_path(phase=args.phase, plan=args.plan, root=root_path)
        phase_plan = parse_phase_plan(plan_path)
        driver_config = load_driver_config(args.config, root=root_path)
        result = run_driver(plan=phase_plan, config=driver_config, root=root_path, dry_run=args.dry_run)
        return result.exit_code
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _coerce_command_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(part, str) or not part for part in value):
        raise ValueError(f"{label} must be a non-empty list of strings")
    return [str(part) for part in value]


def _print_plan_header(plan: PhasePlan, out: Any) -> None:
    print(f"Phase {plan.phase_id}: {plan.title}", file=out)
    print(f"Canary: {plan.canary}", file=out)
    print(f"Plan: {plan.path}", file=out)
