"""The ``orca-*`` subcommands of the private native Bash command bridge.

``httk.workflow._shell_bridge`` mounts these beside its own subcommands through
the ``codes`` registry tier, so each function of ``httk-orca.sh`` is one
invocation of one command here. A legitimately absent answer returns the
bridge's uniform exit code ``1``; a refused call raises, which the bridge
reports as ``2``. ``orca-run`` has its own outcome codes, the same as
``vasp-run``: ``0`` completed, ``20`` crashed, ``21`` nonconverged, ``22``
process failure, ``124`` timeout; ``orca-diagnose`` exits ``20`` when it
found anything, like ``vasp-diagnose``.
"""

import argparse
import json
from pathlib import Path

from httk.workflow.codes import BRIDGE_ABSENT, read_json

from .diagnostics import diagnose_orca
from .inputs import write_orca_input
from .outputs import parse_orca_output
from .reports import run_orca

_RUN_EXIT = {"completed": 0, "crashed": 20, "nonconverged": 21, "process_failure": 22, "timeout": 124}


def add_commands(commands: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register the ``orca-*`` subcommands on the bridge's subparsers.

    :param commands: the bridge's subcommand collection.
    """

    run = commands.add_parser("orca-run")
    run.add_argument("--directory", default=".")
    run.add_argument("--input", default="orca.inp")
    run.add_argument("--output", default="orca.out")
    run.add_argument("--timeout", type=float)
    run.add_argument("argv", nargs=argparse.REMAINDER)
    energy = commands.add_parser("orca-energy")
    energy.add_argument("--output", default="orca.out")
    energy.add_argument("--unit", choices=("eh", "ev"), default="eh")
    converged = commands.add_parser("orca-converged")
    converged.add_argument("--output", default="orca.out")
    diagnose = commands.add_parser("orca-diagnose")
    diagnose.add_argument("--output", default="orca.out")
    diagnose.add_argument("--json", action="store_true")
    write = commands.add_parser("orca-write-input")
    write.add_argument("--options", required=True)
    write.add_argument("--input", default="orca.inp")


def run_command(arguments: argparse.Namespace) -> int:
    """Run one parsed ``orca-*`` subcommand.

    :param arguments: the parsed bridge command line.
    :return: the subcommand's exit code.
    """

    command = arguments.command
    if command == "orca-run":
        argv = arguments.argv[1:] if arguments.argv[:1] == ["--"] else arguments.argv
        if not argv:
            raise ValueError("orca-run needs the ORCA command after --")
        report = run_orca(
            argv,
            directory=arguments.directory,
            input_file=arguments.input,
            output_file=arguments.output,
            timeout=arguments.timeout,
        )
        print(Path(arguments.directory, "orca-run-report.json"))
        return _RUN_EXIT[report.classification]
    if command == "orca-diagnose":
        output = Path(arguments.output)
        diagnostics = diagnose_orca(output.parent, output=output.name)
        if arguments.json:
            print(json.dumps([item.as_mapping() for item in diagnostics], sort_keys=True))
        else:
            for item in diagnostics:
                print(f"{item.code}\t{item.severity}\t{item.summary}")
        return 20 if diagnostics else 0
    if command == "orca-write-input":
        options = dict(read_json(Path(arguments.options)))
        if isinstance(options.get("atoms"), list):
            options["atoms"] = [tuple(atom) for atom in options["atoms"]]
        write_orca_input(arguments.input, **options)
        return 0
    result = parse_orca_output(arguments.output)
    if command == "orca-energy":
        value = result.final_energy_eh if arguments.unit == "eh" else result.final_energy_ev
        if value is None:
            return BRIDGE_ABSENT
        print(f"{value:.16g}")
        return 0
    if command == "orca-converged":
        converged = result.scf_converged and result.optimization_converged is not False
        return 0 if converged else BRIDGE_ABSENT
    raise AssertionError(command)
