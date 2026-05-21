"""Smoke test that the calibration script runs and reports 100% pass.

Important: this fails if any of the canonical benchmark cases stop landing
at the expected verification status. Acts as a high-level regression net
across all three families.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_calibration_report_runs_and_passes() -> None:
    api_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.calibration_report"],
        capture_output=True,
        text=True,
        cwd=api_root,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"Calibration failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "passed:" in result.stdout
    assert "failed:   0" in result.stdout
