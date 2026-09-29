"""Collect hook for the ``orca.singlepoint`` workflow."""

from httk.codes.orca import collect_orca


def collect(record):
    """Extract the final single point energy from the job record.

    :param record: The collected job record.
    :return: The ``total_energy`` output role.
    """
    return collect_orca(record)
