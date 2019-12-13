from pkg_resources import iter_entry_points
from logging import getLogger

_LOG = getLogger(__file__)

for entry_point in iter_entry_points("opentelemetry_patcher"):
    try:
        entry_point.load()().patch()

        _LOG.debug("Patched {}".format(entry_point.name))

    except Exception as error:

        _LOG.exception(
            "Patching of {} failed with: {}".format(entry_point.name, error)
        )
