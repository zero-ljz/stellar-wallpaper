"""Pytest configuration and session-wide fixtures."""

import os
import sys
import tempfile
from pathlib import Path

# Ensure Qt offscreen platform is set if not already specified
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Set up an isolated data directory for all tests so we don't touch user files or fail permissions
_TEST_TEMP_DIR = tempfile.TemporaryDirectory(prefix="stellar_test_")
os.environ["STELLAR_DATA_DIR"] = _TEST_TEMP_DIR.name
os.environ["STELLAR_CACHE_DIR"] = os.path.join(_TEST_TEMP_DIR.name, "cache")


def pytest_sessionfinish(session, exitstatus):
    try:
        _TEST_TEMP_DIR.cleanup()
    except Exception:
        pass
