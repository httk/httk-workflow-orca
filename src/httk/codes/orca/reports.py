"""Supervised ORCA execution and its classified run report."""

import dataclasses
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from httk.workflow.codes import Diagnostic, ProcessReport, ProcessSupervisor, launch_command, write_json_atomic

from .diagnostics import diagnose_orca
from .outputs import OrcaResult, _parse, _read

__all__ = ["OrcaRunReport", "run_orca"]


@dataclass(frozen=True)
class OrcaRunReport:
    """Classified result of one supervised ORCA execution.

    The classification is one of ``completed``, ``crashed`` (an
    ``orca.error_termination`` or ``orca.input_error`` diagnostic),
    ``nonconverged`` (SCF or geometry optimization), ``process_failure`` (a
    nonzero exit or an incomplete output) and ``timeout``.

    :param process: The supervised process result.
    :param classification: The final run classification.
    :param diagnostics: The diagnostics of the finished calculation.
    :param result: What the ORCA output says.
    """

    process: ProcessReport
    classification: str
    diagnostics: tuple[Diagnostic, ...]
    result: OrcaResult

    @property
    def ok(self) -> bool:
        """Whether the calculation terminated normally and converged."""
        return self.classification == "completed"

    def as_mapping(self) -> dict[str, object]:
        """Serialize the report for JSON storage.

        :return: The JSON-compatible report mapping.
        """
        return {
            "format": "httk-orca-run-report",
            "format_version": 1,
            "process": self.process.as_mapping(),
            "classification": self.classification,
            "diagnostics": [item.as_mapping() for item in self.diagnostics],
            "result": {**dataclasses.asdict(self.result), "errors": list(self.result.errors)},
        }

    def write(self, path: str | os.PathLike[str]) -> Path:
        """Write the report as JSON.

        :param path: Write the report to this path.
        :return: The report path.
        """
        destination = Path(path)
        write_json_atomic(destination, self.as_mapping())
        return destination


def run_orca(
    argv: Sequence[str],
    *,
    directory: str | os.PathLike[str] = ".",
    input_file: str = "orca.inp",
    output_file: str = "orca.out",
    timeout: float | None = None,
    launch: bool | None = None,
    termination_grace: float = 10.0,
    report_path: str | os.PathLike[str] = "orca-run-report.json",
) -> OrcaRunReport:
    """Run ORCA under supervision and write a classified report.

    *argv* is the command that starts ORCA; the input file name is appended to
    it as ORCA's positional argument. ORCA starts its own MPI processes for
    ``%pal`` runs and then must be invoked by its absolute path, so pass
    ``["/opt/orca/orca"]`` rather than ``["orca"]`` (a bare ``orca`` on
    ``PATH`` is also often the unrelated GNOME screen reader). Standard output
    goes to *output_file* and standard error beside it with the suffix ``.err``.

    ORCA is not given the attempt's launch prefix by default, since it starts its
    own MPI; ``launch=True`` prepends ``HTTK_WORKFLOW_LAUNCH`` (a command that already
    starts with a launcher such as ``srun`` is then refused with :class:`ValueError`).
    In a confined attempt (``HTTK_WORKFLOW_CONFINED=1``) spanning more than one node
    (``HTTK_WORKFLOW_NODELIST``) ORCA is refused with :class:`ValueError`, as the
    MPI processes it starts cannot reach other nodes from inside the sandbox.

    :param argv: The ORCA command argument vector, without the input file.
    :param directory: Run ORCA in this directory.
    :param input_file: The input file name in *directory*.
    :param output_file: Save standard output under this name in *directory*.
    :param timeout: Stop the process after this many seconds when set.
    :param launch: Prepend the attempt's launch prefix when ``True``; the default
        (``None``) and ``False`` run *argv* as given.
    :param termination_grace: Allow this many seconds for graceful termination.
    :param report_path: Write the report at this directory-relative path.
    :return: The classified run report.
    """

    if os.environ.get("HTTK_WORKFLOW_CONFINED") == "1" and "," in os.environ.get("HTTK_WORKFLOW_NODELIST", ""):
        raise ValueError(
            "distributed ORCA is not supported in a confined attempt: ORCA starts its own MPI processes, "
            "which cannot reach other nodes from inside the job sandbox; request one node"
        )
    command = launch_command(argv, launch=launch is True)
    root = Path(directory).resolve()
    output = root / output_file
    # ponytail: no live monitor or remedy ladder; add them when a real campaign needs them.
    process = ProcessSupervisor().run(
        [*command, input_file],
        timeout=timeout,
        cwd=root,
        termination_grace=termination_grace,
        stdout_path=output,
        stderr_path=output.with_suffix(".err"),
    )
    diagnostics = (*process.diagnostics, *diagnose_orca(root, output=output_file))
    codes = {item.code for item in diagnostics}
    if process.timed_out:
        classification = "timeout"
    elif codes & {"orca.error_termination", "orca.input_error"}:
        classification = "crashed"
    elif process.returncode or "orca.incomplete" in codes:
        classification = "process_failure"
    elif codes & {"orca.scf_not_converged", "orca.optimization_not_converged"}:
        classification = "nonconverged"
    elif any(item.severity in {"error", "fatal"} for item in diagnostics):
        classification = "process_failure"
    else:
        classification = "completed"
    report = OrcaRunReport(process, classification, diagnostics, _parse(_read(output)))
    report.write(root / report_path)
    return report
