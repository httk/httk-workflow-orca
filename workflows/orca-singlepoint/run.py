#!/usr/bin/env python3
"""orca.singlepoint: one ORCA single-point energy of one molecule.

The single ``run`` step stages the molecule (the ``molecule`` input, staged as
``files/molecule.xyz``), writes ``orca.inp`` from the ``keywords``, ``charge``
and ``multiplicity`` parameters, runs ORCA under supervision, and fails with
the first diagnostic code (``orca.error_termination``, ``orca.input_error``,
``orca.scf_not_converged``, ...) when the calculation is not clean.

Settings, resolved job parameter -> ``HTTK_*`` variable -> workspace setting:

* ``orca.command``: required; the command that starts ORCA, which should be its
  absolute path (e.g. ``/opt/orca/orca``): ORCA needs it for parallel runs, and
  a bare ``orca`` on ``PATH`` is often the GNOME screen reader. Without it the
  step fails with ``orca.not_configured``.
"""

import shlex
import shutil
from typing import cast

from httk.workflow import Attempt, Runner

from httk.codes.orca import run_orca, write_orca_input

run = Runner("orca.singlepoint")


@run.step(name="run")
def run_step(a: Attempt) -> None:
    """Prepare and run ORCA, then succeed or fail with what was diagnosed."""

    command = a.setting("orca.command", None)
    if not command:
        a.fail("orca.not_configured", "set the orca.command setting to the absolute path of the orca executable")
        return
    shutil.copyfile(a.payload / "files" / "molecule.xyz", a.workdir / "molecule.xyz")
    try:
        write_orca_input(
            a.workdir / "orca.inp",
            atoms=a.workdir / "molecule.xyz",
            keywords=str(a.parameter("keywords", "B3LYP def2-SVP")),
            charge=cast(int, a.parameter("charge", 0)),
            multiplicity=cast(int, a.parameter("multiplicity", 1)),
        )
    except ValueError as exception:
        a.fail("orca.input_invalid", str(exception))
        return
    try:
        report = run_orca(shlex.split(str(command)), directory=a.workdir)
    except OSError as exception:
        a.fail("orca.failed", f"could not start ORCA: {exception}")
        return
    if not report.ok:
        first = report.diagnostics[0] if report.diagnostics else None
        code = first.code if first else f"orca.{report.classification}"
        a.fail(code, first.summary if first else f"ORCA {report.classification}")
        return
    a.state.merge({"final_energy_eh": report.result.final_energy_eh})
    a.succeed()


if __name__ == "__main__":
    raise SystemExit(run.main())
