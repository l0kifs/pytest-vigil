"""pytest-vigil: A pytest plugin for enhanced test reliability and monitoring."""
import logging

logging.getLogger("pytest_vigil").addHandler(logging.NullHandler())
