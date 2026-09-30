"""The ``orca.calculation`` collector recognizes and collects free-standing runs via ``collect_tree``."""

import bz2
import lzma
import shutil
from pathlib import Path

import pytest
from httk.workflow import claims, collect_tree
from httk.workflow.calculations import content_digest

from conftest import DATA
from httk.codes.orca import EH_TO_EV
from httk.codes.orca.collect import find_outputs

CP2K_HEAD = " DBCSR| CPU Multiplication driver  BLAS (U)\n CP2K| version string:   CP2K version 2026.2\n"
ENERGY = -75.960185412345 * EH_TO_EV


def _run(directory: Path, output: str = "water_sp.out", stem: str = "run") -> Path:
    directory.mkdir(parents=True)
    shutil.copy(DATA / output, directory / f"{stem}.out")
    (directory / f"{stem}.inp").write_text("! HF def2-SVP\n* xyzfile 0 1 water.xyz\n", encoding="utf-8")
    return directory


def test_a_converged_run_is_collected(tmp_path: Path) -> None:
    directory = _run(tmp_path / "water")
    (item,) = collect_tree(tmp_path)
    identity = content_digest(directory, ["run.inp"])
    assert item.missing_collector is None
    assert item.run.source_id == f"orca.calculation:{identity}"
    assert item.outputs["total_energy"].value == pytest.approx(ENERGY)  # type: ignore[attr-defined]


def test_an_unconverged_run_is_claimed_and_degraded(tmp_path: Path) -> None:
    _run(tmp_path / "water", "water_scf_noconv.out")
    (outcome,) = claims(tmp_path)
    assert outcome.kind == "claimed" and outcome.collector == "orca.calculation"
    (item,) = collect_tree(tmp_path)
    assert item.missing_collector is not None and "no converged final single point energy" in item.missing_collector


def test_a_scheduler_log_is_no_candidate(tmp_path: Path) -> None:
    (tmp_path / "slurm-1.out").write_text("Job started\n" * 5, encoding="utf-8")
    assert list(claims(tmp_path)) == []
    assert find_outputs(tmp_path) == ()


def test_several_outputs_are_unclaimed(tmp_path: Path) -> None:
    directory = _run(tmp_path / "water")
    shutil.copy(DATA / "water_sp.out", directory / "other.out")
    (outcome,) = claims(tmp_path)
    assert outcome.kind == "unclaimed"
    assert outcome.reason == "several ORCA outputs: other.out, run.out"
    assert list(collect_tree(tmp_path)) == []


def test_a_missing_input_is_unclaimed(tmp_path: Path) -> None:
    directory = _run(tmp_path / "water")
    (directory / "run.inp").unlink()
    (outcome,) = claims(tmp_path)
    assert (outcome.kind, outcome.reason) == ("unclaimed", "no run.inp beside run.out")


def test_compressed_files_are_collected(tmp_path: Path) -> None:
    directory = _run(tmp_path / "water")
    (directory / "run.out.bz2").write_bytes(bz2.compress((directory / "run.out").read_bytes()))
    (directory / "run.inp.lzma").write_bytes(
        lzma.compress((directory / "run.inp").read_bytes(), format=lzma.FORMAT_ALONE)
    )
    (directory / "run.out").unlink()
    (directory / "run.inp").unlink()
    (item,) = collect_tree(tmp_path)
    assert item.missing_collector is None
    assert item.outputs["total_energy"].value == pytest.approx(ENERGY)  # type: ignore[attr-defined]


def test_the_real_orca_6_banner_is_recognized(tmp_path: Path) -> None:
    shutil.copy(DATA / "real" / "water_hf_solvent_cpcm.out", tmp_path / "a.out")
    shutil.copy(DATA / "real" / "dvb_gopt.out.gz", tmp_path / "b.out.gz")
    assert [path.name for path in find_outputs(tmp_path)] == ["a.out", "b.out.gz"]


def test_another_programs_output_is_not_claimed(tmp_path: Path) -> None:
    (tmp_path / "run.out").write_text(CP2K_HEAD, encoding="utf-8")
    (tmp_path / "run.inp").write_text("&GLOBAL\n&END GLOBAL\n", encoding="utf-8")
    assert find_outputs(tmp_path) == ()
    assert [item for item in claims(tmp_path) if item.collector == "orca.calculation"] == []


def test_an_uppercase_output_finds_its_input(tmp_path: Path) -> None:
    directory = _run(tmp_path / "x", stem="RUN")
    (directory / "RUN.out").rename(directory / "RUN.OUT")
    (item,) = collect_tree(tmp_path)
    assert item.run.source_id == f"orca.calculation:{content_digest(directory, ['RUN.inp'])}"
