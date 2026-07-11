# klippy/extras/mmu/nfc/log.py
#
# Minimal logging shim for the extracted reader drivers.
#
# The original package this was extracted from had a 460-line custom logger
# (log rotation, a separate nfc_reader.log file, optional console echo via
# gcode responses, etc.). None of that is needed for a standalone reader
# module — driver output just needs to reach klippy.log like any other
# Klipper extra. All three drivers only ever use the plain logging.Logger
# call surface (logger.debug/info/warning/error/exception), plus pn532_driver
# additionally imports the three module-level convenience functions below, so
# that's all this shim provides.

import logging

logger = logging.getLogger('mmu_rfid_reader')


def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)
