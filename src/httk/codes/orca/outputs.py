"""Parse the text output of the ORCA quantum-chemistry program.

Pure stdlib parsing: nothing here runs a program or imports *httk* code, so a
result can be read anywhere the output file is. The markers are those of ORCA
5 and 6; they are validated against synthetic fixtures and two real ORCA 6
outputs redistributed by cclib (see the repository's ``tests/data/README.md``).
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

__all__ = ["EH_TO_EV", "OrcaResult", "parse_orca_output"]

#: One Hartree in electronvolts (CODATA 2018), the unit ORCA prints energies in.
EH_TO_EV: float = 27.211386245988

# A parenthetical such as "(SCF not converged)" before the value is tolerated.
_ENERGY = re.compile(r"^\s*FINAL SINGLE POINT ENERGY(?:\s+\([^)]*\))?\s+(-?\d+\.\d+)", re.MULTILINE)
_SCF = re.compile(r"SCF (NOT )?CONVERGED AFTER\s+(\d+)\s+CYCLES")
_ERROR = re.compile(
    r"^.*(?:ORCA finished by error termination in|aborting the run|INPUT ERROR"
    r"|UNRECOGNIZED OR DUPLICATED KEYWORD\(S\) IN SIMPLE INPUT LINE).*$",
    re.MULTILINE,
)
_INPUT_ERROR_MARKERS = ("INPUT ERROR", "UNRECOGNIZED OR DUPLICATED KEYWORD(S) IN SIMPLE INPUT LINE")


@dataclass(frozen=True)
class OrcaResult:
    """What one ORCA output says about its calculation.

    :param final_energy_eh: The last ``FINAL SINGLE POINT ENERGY`` in Eh, or ``None`` when there is
        none or the last SCF did not converge.
    :param scf_converged: Whether the last SCF reported convergence, or ``None`` when none reported.
    :param scf_cycles: The cycle count of the last SCF, or ``None``.
    :param optimization_converged: For a geometry optimization, whether it printed
        ``THE OPTIMIZATION HAS CONVERGED``; ``None`` for other runs.
    :param terminated_normally: Whether ORCA printed ``****ORCA TERMINATED NORMALLY****``.
    :param errors: The error lines (error termination, ``aborting the run``, input errors), in order.
    """

    final_energy_eh: float | None
    scf_converged: bool | None
    scf_cycles: int | None
    optimization_converged: bool | None
    terminated_normally: bool
    errors: tuple[str, ...]

    @property
    def final_energy_ev(self) -> float | None:
        """The converged final single point energy in eV, or ``None``."""
        return None if self.final_energy_eh is None else self.final_energy_eh * EH_TO_EV


def parse_orca_output(path: str | os.PathLike[str]) -> OrcaResult:
    """Parse one saved ORCA standard output.

    :param path: Read the ORCA standard output saved at this path.
    :return: The parsed result.
    :raises FileNotFoundError: If the output file does not exist.
    """

    return _parse(Path(path).read_text(encoding="utf-8", errors="replace"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _is_input_error(message: str) -> bool:
    return any(marker in message for marker in _INPUT_ERROR_MARKERS)


def _parse(text: str) -> OrcaResult:
    energies = _ENERGY.findall(text)
    cycles = _SCF.findall(text)
    errors: list[str] = []
    for line in _ERROR.findall(text):
        # Banner lines such as "*    INPUT ERROR    *" keep only their text.
        message = line.strip(" *\t")
        if message and message not in errors:
            errors.append(message)
    optimization = "GEOMETRY OPTIMIZATION CYCLE" in text or "OPTIMIZATION RUN DONE" in text
    scf_converged = not cycles[-1][0] if cycles else None
    return OrcaResult(
        # Only a converged energy is reported: none after an unconverged last SCF.
        final_energy_eh=float(energies[-1]) if energies and scf_converged is not False else None,
        scf_converged=scf_converged,
        scf_cycles=int(cycles[-1][1]) if cycles else None,
        optimization_converged=("THE OPTIMIZATION HAS CONVERGED" in text) if optimization else None,
        terminated_normally="****ORCA TERMINATED NORMALLY****" in text,
        errors=tuple(errors),
    )
