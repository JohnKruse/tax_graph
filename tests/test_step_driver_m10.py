from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tax_graph.step_driver import main, parse_phase_plan, render_command


def _write_driver_config(path: Path, *, fail_gate: bool = False) -> None:
    pass_value = "0"
    fail_value = "1" if fail_gate else "0"
    payload = {
        "tiers": {
            "worker-standard": {
                "command": [
                    sys.executable,
                    "-c",
                    (
                        "from pathlib import Path; import sys; "
                        "Path(sys.argv[1]).write_text(Path(sys.argv[1]).read_text() + sys.argv[2] + '\\n', "
                        "encoding='utf-8')"
                    ),
                    "{root}/worker.log",
                    "step-{step_number}-{step_tier}",
                ]
            },
            "worker-light": {
                "command": [
                    sys.executable,
                    "-c",
                    (
                        "from pathlib import Path; import sys; "
                        "Path(sys.argv[1]).write_text(Path(sys.argv[1]).read_text() + sys.argv[2] + '\\n', "
                        "encoding='utf-8')"
                    ),
                    "{root}/worker.log",
                    "step-{step_number}-{step_tier}",
                ]
            },
            "worker-heavy": {
                "command": [
                    sys.executable,
                    "-c",
                    (
                        "from pathlib import Path; import sys; "
                        "Path(sys.argv[1]).write_text(Path(sys.argv[1]).read_text() + sys.argv[2] + '\\n', "
                        "encoding='utf-8')"
                    ),
                    "{root}/worker.log",
                    "step-{step_number}-{step_tier}",
                ]
            },
        },
        "gates": [
            {
                "name": "first",
                "command": [sys.executable, "-c", f"raise SystemExit({pass_value})"],
            },
            {
                "name": "second",
                "command": [sys.executable, "-c", f"raise SystemExit({fail_value})"],
            },
        ],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_plan(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "# PHASE M10 - Demo phase   [ ]",
                "",
                "**Canary:** Assembly Line",
                "",
                "## Steps",
                "",
                "- [ ] **Step 1 [worker-standard] - First step.**",
                "  Do the first thing.",
                "",
                "- [ ] **Step 2 [worker-light] - Second step.**",
                "  Do the second thing.",
                "",
                "- [ ] **Step 3 [worker-heavy] - Final gate step.**",
                "  (JOHN's gate - the driver STOPS here).",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.mark.m10
def test_parse_phase_plan_extracts_canary_tiers_and_gate(tmp_path):
    plan_path = tmp_path / "PHASE_M10.md"
    _write_plan(plan_path)

    plan = parse_phase_plan(plan_path)

    assert plan.phase_id == "M10"
    assert plan.canary == "Assembly Line"
    assert [step.tier for step in plan.steps] == ["worker-standard", "worker-light", "worker-heavy"]
    assert plan.steps[2].john_gate is True


@pytest.mark.m10
def test_parse_phase_plan_handles_wrapped_real_plan_headers():
    plan = parse_phase_plan(Path(__file__).resolve().parents[1] / "plans" / "PHASE_M10.md")

    assert [step.number for step in plan.steps] == [1, 2, 3, 4, 5, 6, 7]
    assert plan.steps[4].john_gate is False
    assert "frontier flips" in plan.steps[4].title.lower()


@pytest.mark.m10
def test_run_driver_dry_run_prints_sequence_and_gate_stop(tmp_path, capsys):
    plan_path = tmp_path / "PHASE_M10.md"
    config_path = tmp_path / "driver.yaml"
    _write_plan(plan_path)
    _write_driver_config(config_path)

    result = main(["--plan", str(plan_path), "--config", str(config_path), "--root", str(tmp_path), "--dry-run"])
    out = capsys.readouterr().out

    assert result == 0
    assert "Phase M10: Demo phase" in out
    assert "Step 1 [worker-standard]" in out
    assert "Step 2 [worker-light]" in out
    assert "STOP: Step 3 is marked as John's gate" in out


@pytest.mark.m10
def test_gate_failure_blocks_next_step(tmp_path):
    plan_path = tmp_path / "PHASE_M10.md"
    config_path = tmp_path / "driver.yaml"
    _write_plan(plan_path)
    _write_driver_config(config_path, fail_gate=True)
    (tmp_path / "worker.log").write_text("", encoding="utf-8")

    exit_code = main(["--plan", str(plan_path), "--config", str(config_path), "--root", str(tmp_path)])

    assert exit_code == 1
    log_lines = (tmp_path / "worker.log").read_text(encoding="utf-8").splitlines()
    assert log_lines == ["step-1-worker-standard"]


@pytest.mark.m10
def test_render_command_expands_step_context():
    command = render_command(
        ("runner", "{phase_id}", "{step_number}", "{step_tier}", "{prompt_file}"),
        {
            "phase_id": "M10",
            "step_number": "2",
            "step_tier": "worker-light",
            "prompt_file": "C:/temp/prompt.txt",
        },
    )

    assert command == ["runner", "M10", "2", "worker-light", "C:/temp/prompt.txt"]


@pytest.mark.m10
def test_standalone_script_runs_from_tools_path(tmp_path):
    plan_path = tmp_path / "PHASE_M10.md"
    config_path = tmp_path / "driver.yaml"
    _write_plan(plan_path)
    _write_driver_config(config_path)

    result = subprocess.run(
        [sys.executable, str(Path("tools/step_driver.py").resolve()), "--plan", str(plan_path), "--config", str(config_path), "--root", str(tmp_path), "--dry-run"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Phase M10: Demo phase" in result.stdout
