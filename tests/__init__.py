"""Test suite package initialiser to configure shared settings."""

from pathlib import Path
import os

TEST_LEARNING_STATE = Path(__file__).parent / "test_learning_state.json"
os.environ.setdefault("BOM_EXTRACTOR_LEARNING_PATH", str(TEST_LEARNING_STATE))
try:
    if TEST_LEARNING_STATE.exists():
        TEST_LEARNING_STATE.unlink()
except OSError:
    pass
