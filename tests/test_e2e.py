"""End to end with a real ORCA: install, run, and collect the ``orca.singlepoint`` workflow.

Runs only when ``HTTK_TEST_ORCA_COMMAND`` names a real, licensed ORCA (its
absolute path; there is no ``PATH`` lookup, because ``orca`` on ``PATH`` is
often the GNOME screen reader). The workflow is installed as the
``httk_plugin.toml`` plugin of this repository, as ``httk plugin install``
does, into the test's isolated data home.
"""

import shlex
from pathlib import Path

import pytest

from conftest import orca_command, requires_orca, run_singlepoint
from httk.codes.orca import EH_TO_EV

pytestmark = [requires_orca, pytest.mark.slow]


def test_orca_singlepoint_runs_orca_and_collects_the_energy(
    tmp_path: Path, installed_plugin: None, capsys: pytest.CaptureFixture[str]
) -> None:
    energy = run_singlepoint(tmp_path, shlex.join(orca_command() or ()), capsys, keywords="HF def2-SVP")
    # A loose sanity bound on HF/def2-SVP water, not a reference value; the step
    # succeeding already means ****ORCA TERMINATED NORMALLY**** with a converged SCF.
    assert energy == pytest.approx(-75.96 * EH_TO_EV, abs=0.05 * EH_TO_EV)
