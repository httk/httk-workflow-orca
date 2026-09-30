"""Building blocks for the collect hooks of ORCA workflows."""

from pathlib import Path

from httk.core import DataRecord

from .outputs import parse_orca_output

__all__ = ["read_total_energy"]

_TOTAL_ENERGY_DEFINITION = "https://schemas.httk.org/defs/v0.1/properties/core/total_energy"
_TOTAL_ENERGY_NAME = "_httk_total_energy"


def read_total_energy(path: Path) -> DataRecord:
    """Read the final single point energy, in eV, from one ORCA output file.

    :param path: The ORCA output file.
    :return: The energy as a ``total_energy`` property record.
    :raises ValueError: If the output holds no converged final single point energy,
        or is a geometry optimization that did not converge.
    """

    result = parse_orca_output(path)
    energy = result.final_energy_ev
    if energy is None:
        raise ValueError(f"{path} holds no converged final single point energy")
    if result.optimization_converged is False:
        raise ValueError(f"{path} is a geometry optimization that did not converge")
    return DataRecord.from_value(_TOTAL_ENERGY_DEFINITION, _TOTAL_ENERGY_NAME, energy)
