"""Classify a finished ORCA calculation into stable diagnostics."""

import os
from pathlib import Path

from httk.workflow.codes import Diagnostic

from .outputs import _is_input_error, _parse, _read

__all__ = ["diagnose_orca"]


def diagnose_orca(directory: str | os.PathLike[str] = ".", *, output: str = "orca.out") -> tuple[Diagnostic, ...]:
    """Diagnose an ORCA calculation from its saved standard output.

    The codes are stable: ``orca.input_error`` (fatal; ORCA refused the input,
    e.g. an unrecognized simple-input keyword), ``orca.error_termination``
    (fatal; ``ORCA finished by error termination in ...`` or ``aborting the
    run``), ``orca.scf_not_converged`` (error; the last SCF reported ``SCF NOT
    CONVERGED``), ``orca.optimization_not_converged`` (error; a geometry
    optimization terminated normally without ``THE OPTIMIZATION HAS
    CONVERGED``), and ``orca.incomplete`` (error; neither normal nor error
    termination, e.g. a killed process). An input error is reported instead of
    the error termination it causes. The summary of an error is the
    ``error termination in <PROGRAM>`` line when there is one, and the
    evidence holds every error line. A converged, normally terminated run has
    none. A missing output file is diagnosed like an empty one.

    :param directory: Read the output file from this directory.
    :param output: The name of the saved ORCA standard output in *directory*.
    :return: The diagnostics, empty for a clean run.
    """

    result = _parse(_read(Path(directory) / output))
    diagnostics: list[Diagnostic] = []
    input_errors = [item for item in result.errors if _is_input_error(item)]
    if input_errors:
        diagnostics.append(Diagnostic("orca.input_error", "fatal", input_errors[-1], output, "\n".join(result.errors)))
    elif result.errors:
        # The "error termination in <PROGRAM>" line names the failing program; prefer it.
        termination = [item for item in result.errors if item.startswith("ORCA finished by error termination")]
        summary = (termination or list(result.errors))[0]
        diagnostics.append(Diagnostic("orca.error_termination", "fatal", summary, output, "\n".join(result.errors)))
    elif not result.terminated_normally:
        diagnostics.append(
            Diagnostic("orca.incomplete", "error", f"{output} has no ****ORCA TERMINATED NORMALLY**** line", output)
        )
    if result.scf_converged is False:
        diagnostics.append(
            Diagnostic("orca.scf_not_converged", "error", f"SCF NOT CONVERGED AFTER {result.scf_cycles} CYCLES", output)
        )
    if result.optimization_converged is False and result.terminated_normally:
        diagnostics.append(
            Diagnostic("orca.optimization_not_converged", "error", "the geometry optimization did not converge", output)
        )
    return tuple(diagnostics)
