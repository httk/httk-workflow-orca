"""The ``orca`` code is registered through the ``codes`` registry tier, with its citation."""

import argparse
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import httk.core  # noqa: F401  (importing httk.core runs registry discovery)
from httk.core.register import code_support, known_codes


def test_orca_is_a_known_code_with_its_packaged_bash_api() -> None:
    assert "orca" in known_codes()
    assert code_support("orca").bash_api_path() == Path(str(files("httk.codes.orca").joinpath("httk-orca.sh")))


def test_the_bridge_mounts_the_orca_commands() -> None:
    parser = argparse.ArgumentParser()
    code_support("orca").resolve_bridge().add_commands(parser.add_subparsers(dest="command"))
    assert parser.parse_args(["orca-energy"]).command == "orca-energy"


def test_the_orca_credit_is_registered_on_import() -> None:
    script = """
from httk.core import credits
assert "Calculations with ORCA" not in credits.entries()
import httk.codes.orca
(reference,) = credits.entries()["Calculations with ORCA"]
"""
    subprocess.run([sys.executable, "-c", script], check=True)
