"""Collect hook for the ``orca.singlepoint`` workflow.

The run leaves ``orca.out`` in the persistent workdir.
"""

from httk.codes.orca.collect import read_total_energy


def collect(record):
    """Return the final single point energy of the run.

    :param record: The collected job record.
    :return: The ``total_energy`` output role.
    """
    return {"total_energy": read_total_energy(record.result_file("orca.out"))}
