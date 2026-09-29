"""``write_orca_input`` writes molecular ORCA inputs."""

import os
import subprocess
from pathlib import Path

import pytest

from conftest import DATA, orca_command, requires_orca
from httk.codes.orca import parse_orca_output, write_orca_input

_WATER_LINES = [
    "* xyz 0 1",
    "O 0.0 0.0 0.1173",
    "H 0.0 0.7572 -0.4692",
    "H 0.0 -0.7572 -0.4692",
    "*",
]


def test_an_xyz_file_with_defaults(tmp_path: Path) -> None:
    write_orca_input(tmp_path / "orca.inp", atoms=DATA / "water.xyz")
    assert (tmp_path / "orca.inp").read_text(encoding="utf-8").splitlines() == ["! B3LYP def2-SVP", *_WATER_LINES]


def test_atoms_keywords_and_blocks(tmp_path: Path) -> None:
    write_orca_input(
        tmp_path / "orca.inp",
        atoms=[("O", 0, 0, 0.1173), ("H", 0, 0.7572, -0.4692), ("H", 0, -0.7572, -0.4692)],
        keywords=["HF", "def2-SVP", "TightSCF"],
        charge=1,
        multiplicity=2,
        nprocs=4,
        maxcore_mb=2000,
        blocks={"scf": "MaxIter 200\nConvForced true"},
    )
    assert (tmp_path / "orca.inp").read_text(encoding="utf-8") == "\n".join(
        [
            "! HF def2-SVP TightSCF",
            "%pal nprocs 4 end",
            "%maxcore 2000",
            "%scf",
            "  MaxIter 200",
            "  ConvForced true",
            "end",
            "* xyz 1 2",
            *_WATER_LINES[1:],
            "",
        ]
    )


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"keywords": " "}, "keywords"),
        ({"keywords": "HF\nOpt"}, "keywords"),
        ({"charge": 0.5}, "charge"),
        ({"multiplicity": 0}, "multiplicity"),
        ({"multiplicity": True}, "multiplicity"),
        ({"nprocs": -1}, "nprocs"),
        ({"maxcore_mb": 0}, "maxcore_mb"),
        ({"blocks": {"bad name": "x"}}, "block name"),
        ({"nprocs": 2, "blocks": {"pal": "nprocs 4"}}, "conflicts"),
        ({"atoms": []}, "no atoms"),
        ({"atoms": [("O", 0, 0)]}, "symbol, x, y, z"),
        ({"atoms": [("O H", 0, 0, 0)]}, "symbol, x, y, z"),
        ({"atoms": [("O", 0, 0, float("nan"))]}, "finite"),
    ],
)
def test_invalid_options_are_refused(tmp_path: Path, options: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        write_orca_input(tmp_path / "orca.inp", **({"atoms": DATA / "water.xyz"} | options))  # type: ignore[arg-type]


def test_a_malformed_xyz_file_is_refused(tmp_path: Path) -> None:
    (tmp_path / "short.xyz").write_text("3\ncomment\nO 0 0 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="declares 3 atoms but lists 1"):
        write_orca_input(tmp_path / "orca.inp", atoms=tmp_path / "short.xyz")
    (tmp_path / "bad.xyz").write_text("one\ncomment\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not an .xyz file"):
        write_orca_input(tmp_path / "orca.inp", atoms=str(tmp_path / "bad.xyz"))


@requires_orca
def test_the_real_orca_accepts_the_input(tmp_path: Path) -> None:
    command = orca_command()
    assert command is not None
    write_orca_input(tmp_path / "orca.inp", atoms=DATA / "water.xyz", keywords="HF def2-SVP")
    with (tmp_path / "orca.out").open("wb") as output:
        subprocess.run(
            [*command, "orca.inp"],
            cwd=tmp_path,
            stdout=output,
            stderr=subprocess.DEVNULL,
            env=os.environ | {"OMP_NUM_THREADS": "1"},
            check=True,
            timeout=600,
        )
    result = parse_orca_output(tmp_path / "orca.out")
    assert result.scf_converged and result.terminated_normally
    # A loose sanity bound on HF/def2-SVP water, not a reference value.
    assert result.final_energy_eh == pytest.approx(-75.96, abs=0.05)
