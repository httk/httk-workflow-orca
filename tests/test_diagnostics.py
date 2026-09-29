"""``diagnose_orca`` maps finished calculations to the stable ``orca.*`` codes."""

from pathlib import Path

import pytest

from conftest import DATA
from httk.codes.orca import diagnose_orca


def _codes(directory: Path, output: str) -> list[tuple[str, str]]:
    return [(item.code, item.severity) for item in diagnose_orca(directory, output=output)]


@pytest.mark.parametrize("output", ["water_sp.out", "water_opt.out"])
def test_clean_runs_have_no_diagnostics(output: str) -> None:
    assert diagnose_orca(DATA, output=output) == ()


def test_an_unconverged_scf_is_an_error() -> None:
    assert _codes(DATA, "water_scf_noconv.out") == [("orca.scf_not_converged", "error")]


def test_an_error_termination_is_fatal_and_names_the_program() -> None:
    assert _codes(DATA, "water_error.out") == [("orca.error_termination", "fatal"), ("orca.scf_not_converged", "error")]
    (diagnostic, _) = diagnose_orca(DATA, output="water_error.out")
    assert diagnostic.summary == "ORCA finished by error termination in SCF"
    assert diagnostic.evidence is not None and "aborting the run" in diagnostic.evidence


def test_an_input_error_replaces_the_error_termination(tmp_path: Path) -> None:
    (diagnostic,) = diagnose_orca(DATA, output="water_input_error.out")
    assert (diagnostic.code, diagnostic.severity) == ("orca.input_error", "fatal")
    assert "UNRECOGNIZED" in diagnostic.summary
    text = (DATA / "water_input_error.out").read_text(encoding="utf-8")
    (tmp_path / "orca.out").write_text(text + "ORCA finished by error termination in ORCA\n", encoding="utf-8")
    assert _codes(tmp_path, "orca.out") == [("orca.input_error", "fatal")]


def test_an_optimization_that_ended_unconverged_is_an_error(tmp_path: Path) -> None:
    text = (DATA / "water_opt.out").read_text(encoding="utf-8").replace("THE OPTIMIZATION HAS CONVERGED", "")
    (tmp_path / "orca.out").write_text(text, encoding="utf-8")
    assert _codes(tmp_path, "orca.out") == [("orca.optimization_not_converged", "error")]


def test_a_truncated_or_missing_output_is_incomplete(tmp_path: Path) -> None:
    assert _codes(DATA, "water_truncated.out") == [("orca.incomplete", "error")]
    assert _codes(tmp_path, "absent.out") == [("orca.incomplete", "error")]
    text = (DATA / "water_opt.out").read_text(encoding="utf-8")
    (tmp_path / "orca.out").write_text(text[: len(text) // 2], encoding="utf-8")
    # A killed optimization is incomplete, not unconverged.
    assert _codes(tmp_path, "orca.out") == [("orca.incomplete", "error")]
