"""``read_total_energy`` reads one ORCA output; the packaged hook finds it with ``result_file``."""

import runpy
import shutil
from pathlib import Path, PurePosixPath

import pytest
from httk.core import DataRecord
from httk.workflow.collecting import JobRecord

from conftest import DATA
from httk.codes.orca import EH_TO_EV
from httk.codes.orca.collect import read_total_energy

HOOK = Path(__file__).parent.parent / "workflows" / "orca-singlepoint" / "collect.py"
JOB_ID = "12345678-1234-4234-8234-123456789abc"


def test_the_energy_is_read_in_ev() -> None:
    assert read_total_energy(DATA / "water_sp.out").value == pytest.approx(-75.960185412345 * EH_TO_EV)


def test_unconverged_outputs_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no converged final single point energy"):
        read_total_energy(DATA / "water_scf_noconv.out")
    text = (DATA / "water_opt.out").read_text(encoding="utf-8").replace("THE OPTIMIZATION HAS CONVERGED", "")
    (tmp_path / "orca.out").write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="did not converge"):
        read_total_energy(tmp_path / "orca.out")


def test_the_packaged_hook_reads_the_workdir_output(tmp_path: Path) -> None:
    (tmp_path / "run").mkdir()
    shutil.copy(DATA / "water_sp.out", tmp_path / "run" / "orca.out")
    record = JobRecord(
        workspace_root=tmp_path,
        workspace_id="ws",
        job_id=JOB_ID,
        job_key=f"job--{JOB_ID}",
        job={},
        runner_provenance=None,
        state="succeeded",
        failure=None,
        placement=PurePosixPath("jobs"),
        payload_path=PurePosixPath(f"jobs/job--{JOB_ID}"),
        workdir_path=PurePosixPath("run"),
        data_path=None,
        provenance={},
        runner_steps=None,
        children={},
        declarations={},
    )
    outputs = runpy.run_path(str(HOOK))["collect"](record)
    assert set(outputs) == {"total_energy"}
    assert isinstance(outputs["total_energy"], DataRecord)
    assert outputs["total_energy"].value == pytest.approx(-75.960185412345 * EH_TO_EV)
