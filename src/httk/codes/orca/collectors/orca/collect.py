"""Collect hook for the ``orca.calculation`` collector.

The directory holds one ORCA output, found by its banner, whatever its name.
"""

from httk.workflow.collecting import JobRecord

from httk.codes.orca.collect import find_outputs, read_total_energy


def collect(record: JobRecord):
    """Return the final single point energy of the calculation.

    :param record: The stand-in job record of the directory.
    :return: The ``total_energy`` output role.
    """
    if record.workdir is None:
        raise ValueError("the job has no working directory")
    (output,) = find_outputs(record.workdir)
    return {"total_energy": read_total_energy(output)}
