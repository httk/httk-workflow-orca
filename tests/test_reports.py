"""``run_orca`` classifies a supervised run and writes its report.

A Python stand-in "orca" prints a synthetic fixture (``tests/data``), so the
classification and the ``orca.singlepoint`` workflow are exercised without a
real ORCA. These stand-in tests are the strongest end-to-end check available
without an ORCA license; they prove the plumbing, not the parsers against real
ORCA output.
"""

import json
import shlex
import sys
from pathlib import Path

import pytest

from conftest import DATA, run_singlepoint
from httk.codes.orca import EH_TO_EV, run_orca

# Prints the named fixture and exits with a code; run_orca appends the input
# file name, which it ignores.
_REPLAY = "import sys; sys.stdout.write(open(sys.argv[1]).read()); sys.exit(int(sys.argv[2]))"


def _replay(output: str, code: int = 0) -> list[str]:
    return [sys.executable, "-c", _REPLAY, str(DATA / output), str(code)]


@pytest.mark.parametrize(
    ("argv", "classification"),
    [
        (_replay("water_sp.out"), "completed"),
        (_replay("water_opt.out"), "completed"),
        (_replay("water_scf_noconv.out"), "nonconverged"),
        (_replay("water_error.out", 1), "crashed"),
        (_replay("water_input_error.out", 1), "crashed"),
        (_replay("water_truncated.out"), "process_failure"),
        (_replay("water_sp.out", 3), "process_failure"),
    ],
)
def test_the_run_is_classified_and_reported(tmp_path: Path, argv: list[str], classification: str) -> None:
    report = run_orca(argv, directory=tmp_path)
    assert report.classification == classification
    assert report.ok == (classification == "completed")
    assert report.process.argv[-1] == "orca.inp"
    saved = json.loads((tmp_path / "orca-run-report.json").read_text(encoding="utf-8"))
    assert saved["format"] == "httk-orca-run-report" and saved["classification"] == classification
    if classification == "completed":
        assert saved["result"]["final_energy_eh"] < -75.9
        assert report.diagnostics == ()


def test_a_clean_rerun_in_the_same_directory_is_not_read_as_the_earlier_failure(tmp_path: Path) -> None:
    assert run_orca(_replay("water_error.out", 1), directory=tmp_path).classification == "crashed"
    assert run_orca(_replay("water_sp.out"), directory=tmp_path).classification == "completed"


def test_a_rerun_does_not_auto_start_from_the_earlier_wavefunction(tmp_path: Path) -> None:
    for name in ("orca.inp", "orca.xyz", "orca.gbw", "orca.densities", "orca.scfp", "orca.scfr"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    # Records which of the input's files ORCA would have found at start.
    found = "import os; names = ' '.join(os.listdir('.')); open('found', 'w').write(names)"
    run_orca([sys.executable, "-c", found], directory=tmp_path)
    present = set((tmp_path / "found").read_text(encoding="utf-8").split())
    assert {"orca.inp", "orca.xyz"} <= present
    assert not present & {"orca.gbw", "orca.densities", "orca.scfp", "orca.scfr"}

    (tmp_path / "orca.gbw").write_text("orca.gbw", encoding="utf-8")
    run_orca([sys.executable, "-c", found], directory=tmp_path, autostart=True)
    assert "orca.gbw" in (tmp_path / "found").read_text(encoding="utf-8").split()
    assert (tmp_path / "orca.gbw").read_text(encoding="utf-8") == "orca.gbw"
    assert all((tmp_path / name).read_text(encoding="utf-8") == name for name in ("orca.inp", "orca.xyz"))


# A stand-in ORCA for the workflow: checks it was given a written input, then
# prints the converged water fixture.
_STAND_IN = f"""import sys
text = open(sys.argv[1]).read()
assert text.startswith("! HF def2-SVP\\n") and "* xyz 0 1" in text, text
sys.stdout.write(open({str(DATA / "water_sp.out")!r}).read())
"""


@pytest.mark.slow
def test_stand_in_orca_singlepoint_workflow_runs_and_collects(
    tmp_path: Path, installed_plugin: None, capsys: pytest.CaptureFixture[str]
) -> None:
    script = tmp_path / "stand_in_orca.py"
    script.write_text(_STAND_IN, encoding="utf-8")
    energy = run_singlepoint(tmp_path, shlex.join([sys.executable, str(script)]), capsys, keywords="HF def2-SVP")
    assert energy == pytest.approx(-75.960185412345 * EH_TO_EV)


@pytest.mark.slow
def test_the_workflow_refuses_to_guess_the_orca_command(tmp_path: Path, installed_plugin: None) -> None:
    from httk.workflow import TaskManager, Workspace
    from httk.workflow.collecting import job_records
    from httk.workflow.scaffold import new_job

    workspace = Workspace.initialize(tmp_path / "workspace")
    job = new_job(workspace, "orca.singlepoint", inputs={"molecule": DATA / "water.xyz"}, install=True)
    with TaskManager(workspace, heartbeat_interval=0.01) as manager:
        manager.run_until_idle(timeout=120.0)
    [record] = job_records(workspace, states=("succeeded", "failed"))
    assert (record.job_id, record.state) == (job.job_id, "failed")
    assert record.failure is not None and record.failure.code == "orca.not_configured", record.failure
