"""``parse_orca_output`` reads the ORCA 5/6 markers of the synthetic fixtures and of two real outputs."""

import gzip
from pathlib import Path

import pytest

from conftest import DATA
from httk.codes.orca import EH_TO_EV, diagnose_orca, parse_orca_output


def test_a_converged_single_point() -> None:
    result = parse_orca_output(DATA / "water_sp.out")
    assert result.final_energy_eh == -75.960185412345
    assert result.final_energy_ev == pytest.approx(-75.960185412345 * EH_TO_EV)
    assert (result.scf_converged, result.scf_cycles, result.optimization_converged) == (True, 11, None)
    assert (result.terminated_normally, result.errors) == (True, ())


def test_an_unconverged_scf() -> None:
    result = parse_orca_output(DATA / "water_scf_noconv.out")
    assert result.final_energy_eh is None and result.final_energy_ev is None
    assert (result.scf_converged, result.scf_cycles, result.terminated_normally, result.errors) == (
        False,
        125,
        True,
        (),
    )


def test_an_error_termination_collects_the_error_lines_once() -> None:
    result = parse_orca_output(DATA / "water_error.out")
    assert (result.scf_converged, result.terminated_normally) == (False, False)
    assert result.errors == (
        "This wavefunction IS NOT CONVERGED! aborting the run",
        "ORCA finished by error termination in SCF",
        ".... aborting the run",
    )


def test_an_input_error_strips_the_banner() -> None:
    result = parse_orca_output(DATA / "water_input_error.out")
    assert result.errors == ("INPUT ERROR", "UNRECOGNIZED OR DUPLICATED KEYWORD(S) IN SIMPLE INPUT LINE")
    assert (result.final_energy_eh, result.scf_converged, result.terminated_normally) == (None, None, False)


def test_an_optimization_reports_its_last_energy_and_convergence() -> None:
    result = parse_orca_output(DATA / "water_opt.out")
    assert (result.final_energy_eh, result.scf_cycles) == (-75.961098765432, 6)
    assert (result.optimization_converged, result.terminated_normally) == (True, True)


def test_a_truncated_output_has_neither_energy_nor_termination() -> None:
    result = parse_orca_output(DATA / "water_truncated.out")
    assert (result.final_energy_eh, result.terminated_normally, result.errors) == (None, False, ())


def test_an_annotated_energy_line_is_read() -> None:
    from httk.codes.orca.outputs import _parse

    assert _parse("FINAL SINGLE POINT ENERGY (SCF not converged)   -75.5\n").final_energy_eh == -75.5


def test_an_energy_after_an_unconverged_scf_is_not_reported() -> None:
    from httk.codes.orca.outputs import _parse

    text = (
        "SCF NOT CONVERGED AFTER 125 CYCLES\nFINAL SINGLE POINT ENERGY       -75.5\n****ORCA TERMINATED NORMALLY****\n"
    )
    assert (_parse(text).final_energy_eh, _parse(text).scf_converged) == (None, False)


def test_a_real_orca_6_single_point() -> None:
    result = parse_orca_output(DATA / "real" / "water_hf_solvent_cpcm.out")
    assert (result.final_energy_eh, result.scf_converged, result.scf_cycles) == (-74.967672596588, True, 9)
    assert (result.optimization_converged, result.terminated_normally, result.errors) == (None, True, ())


def test_a_real_orca_6_geometry_optimization(tmp_path: Path) -> None:
    output = tmp_path / "dvb_gopt.out"
    output.write_bytes(gzip.decompress((DATA / "real" / "dvb_gopt.out.gz").read_bytes()))
    result = parse_orca_output(output)
    assert (result.final_energy_eh, result.scf_converged, result.scf_cycles) == (-382.055133399486, True, 3)
    assert (result.optimization_converged, result.terminated_normally, result.errors) == (True, True, ())
    assert diagnose_orca(tmp_path, output="dvb_gopt.out") == ()


def test_a_compressed_output_parses_like_the_plain_one(tmp_path: Path) -> None:
    import bz2

    (tmp_path / "sp.out.bz2").write_bytes(bz2.compress((DATA / "water_sp.out").read_bytes()))
    assert parse_orca_output(tmp_path / "sp.out.bz2") == parse_orca_output(DATA / "water_sp.out")
