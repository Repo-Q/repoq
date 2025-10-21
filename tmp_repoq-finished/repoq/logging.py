from __future__ import annotations
import logging, sys

def setup_logging(verbosity: int = 0):
    level = logging.WARNING
    if verbosity == 1: level = logging.INFO
    elif verbosity >= 2: level = logging.DEBUG
    logging.basicConfig(stream=sys.stdout, level=level, format="%(levelname)s %(message)s")
