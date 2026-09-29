"""Extract workflow outputs from a collected ORCA job."""

from httk.core import DataRecord
from httk.workflow.collecting import JobRecord

from .outputs import parse_orca_output

__all__ = ["collect_orca"]

_TOTAL_ENERGY_DEFINITION = "https://schemas.httk.org/defs/v0.1/properties/core/total_energy"
_TOTAL_ENERGY_NAME = "_httk_total_energy"


def collect_orca(record: JobRecord, *, output: str = "orca.out") -> dict[str, object]:
    """Extract the final single point energy, in eV, of one ORCA job.

    The output is read from the job's published data when it has any, else
    from its persistent workdir.

    :param record: The collected job record.
    :param output: The ORCA output file name.
    :return: The ``total_energy`` output role.
    :raises ValueError: If the output is missing, holds no converged final single point energy,
        or is an unconverged geometry optimization.
    """

    root = record.data if record.data is not None else record.workdir
    identity = f"{record.workspace_id}:{record.job_id}"
    if root is None or not (root / output).is_file():
        raise ValueError(f"{identity}: expected the ORCA output {output!r}, but the job has none")
    result = parse_orca_output(root / output)
    energy = result.final_energy_ev
    if energy is None:
        raise ValueError(f"{identity}: {root / output} holds no converged final single point energy")
    if result.optimization_converged is False:
        raise ValueError(f"{identity}: {root / output} is a geometry optimization that did not converge")
    return {"total_energy": DataRecord.from_value(_TOTAL_ENERGY_DEFINITION, _TOTAL_ENERGY_NAME, energy)}
