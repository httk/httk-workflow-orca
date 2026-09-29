"""The ``orca-*`` bridge commands and the Bash API that forwards to them.

Code verbs need no attempt, so they run straight through the shell bridge.
"""

import json
import os
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import pytest

from conftest import DATA
from httk.codes.orca import EH_TO_EV


def _bridge(cwd: Path, *arguments: str) -> "subprocess.CompletedProcess[str]":
    environment = {name: value for name, value in os.environ.items() if not name.startswith("HTTK_WORKFLOW_")}
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    return subprocess.run(
        [sys.executable, "-m", "httk.workflow._shell_bridge", *arguments],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_energy_and_convergence_answers_and_absences(tmp_path: Path) -> None:
    energy = _bridge(tmp_path, "orca-energy", "--output", str(DATA / "water_sp.out"))
    assert (energy.returncode, energy.stdout) == (0, "-75.960185412345\n")
    in_ev = _bridge(tmp_path, "orca-energy", "--output", str(DATA / "water_sp.out"), "--unit", "ev")
    assert float(in_ev.stdout) == pytest.approx(-75.960185412345 * EH_TO_EV)
    for output in ("water_sp.out", "water_opt.out"):
        assert _bridge(tmp_path, "orca-converged", "--output", str(DATA / output)).returncode == 0
    for verb in ("orca-energy", "orca-converged"):
        absent = _bridge(tmp_path, verb, "--output", str(DATA / "water_scf_noconv.out"))
        assert (absent.returncode, absent.stdout) == (1, "")
    refused = _bridge(tmp_path, "orca-energy", "--output", str(tmp_path / "missing.out"))
    assert refused.returncode == 2


def test_diagnose_prints_codes_and_json(tmp_path: Path) -> None:
    clean = _bridge(tmp_path, "orca-diagnose", "--output", str(DATA / "water_sp.out"))
    assert (clean.returncode, clean.stdout) == (0, "")
    failed = _bridge(tmp_path, "orca-diagnose", "--output", str(DATA / "water_input_error.out"), "--json")
    assert failed.returncode == 20
    assert [item["code"] for item in json.loads(failed.stdout)] == ["orca.input_error"]


def test_write_input_then_run_with_a_replayed_orca(tmp_path: Path) -> None:
    options = {"atoms": [["O", 0, 0, 0.1173], ["H", 0, 0.7572, -0.4692]], "keywords": ["HF", "def2-SVP"]}
    (tmp_path / "options.json").write_text(json.dumps(options), encoding="utf-8")
    assert _bridge(tmp_path, "orca-write-input", "--options", "options.json").returncode == 0
    assert (
        (tmp_path / "orca.inp").read_text(encoding="utf-8").startswith("! HF def2-SVP\n* xyz 0 1\nO 0.0 0.0 0.1173\n")
    )

    replay = "import sys; sys.stdout.write(open(sys.argv[1]).read())"
    ran = _bridge(tmp_path, "orca-run", "--", sys.executable, "-c", replay, str(DATA / "water_scf_noconv.out"))
    assert (ran.returncode, ran.stdout) == (21, "orca-run-report.json\n")
    report = json.loads((tmp_path / "orca-run-report.json").read_text(encoding="utf-8"))
    assert report["classification"] == "nonconverged"


def test_the_bash_api_forwards_to_the_bridge(tmp_path: Path) -> None:
    workflow_api = files("httk.workflow").joinpath("languages", "bash", "httk-workflow.sh")
    orca_api = files("httk.codes.orca").joinpath("httk-orca.sh")
    script = (
        f'source "{workflow_api}"; source "{orca_api}"; [ "$HTTK_ORCA_BASH_API_VERSION" = 1 ]; '
        f'httk_orca_energy --output "{DATA / "water_sp.out"}" --unit eh'
    )
    environment = {name: value for name, value in os.environ.items() if not name.startswith("HTTK_WORKFLOW_")}
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    environment["HTTK_WORKFLOW_PYTHON"] = sys.executable
    result = subprocess.run(
        ["bash", "-c", script], cwd=tmp_path, env=environment, text=True, capture_output=True, check=False
    )
    assert (result.returncode, result.stdout) == (0, "-75.960185412345\n"), result.stderr
    unguarded = subprocess.run(
        ["bash", "-c", f'source "{orca_api}"; httk_orca_energy'], text=True, capture_output=True, check=False
    )
    assert unguarded.returncode == 2 and "source HTTK_WORKFLOW_BASH_API" in unguarded.stderr
