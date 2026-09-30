"""Register the ORCA code support implemented by :mod:`httk.codes.orca`."""

from httk.core.register import register_code, register_collector

register_code("orca", bridge="httk.codes.orca._bridge", bash_api="httk.codes.orca:httk-orca.sh")
register_collector("orca.calculation", package="httk.codes.orca:collectors/orca")
