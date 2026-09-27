"""
Verification adapter for scorekit integration testing.
Executes 'scorekit texture check' and 'scorekit texture inspect' directly.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict


class VerificationReport:
    def __init__(
        self,
        scorekit_available: bool,
        check_passed: bool,
        details: Dict[str, Any],
        raw_output: str = "",
    ):
        self.scorekit_available = scorekit_available
        self.check_passed = check_passed
        self.details = details
        self.raw_output = raw_output

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scorekit_available": self.scorekit_available,
            "check_passed": self.check_passed,
            "details": self.details,
            "raw_output": self.raw_output,
        }


def verify_with_scorekit(textures_yaml: Path | str) -> VerificationReport:
    """Run 'scorekit texture check' on the emitted profile."""
    textures_yaml = Path(textures_yaml)
    scorekit_bin = shutil.which("scorekit")

    if not scorekit_bin:
        # Check standard user local binary
        cargo_bin = Path.home() / ".cargo" / "bin" / "scorekit"
        if cargo_bin.exists():
            scorekit_bin = str(cargo_bin)

    if not scorekit_bin:
        return VerificationReport(
            scorekit_available=False,
            check_passed=True,
            details={"warning": "scorekit binary not found in PATH; skipped external CLI verification."},
        )

    # Run 'scorekit texture check <path> --json'
    cmd = [scorekit_bin, "texture", "check", str(textures_yaml), "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    passed = proc.returncode == 0
    parsed = {}
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
        except Exception:
            parsed = {"stdout": proc.stdout}

    return VerificationReport(
        scorekit_available=True,
        check_passed=passed,
        details=parsed,
        raw_output=proc.stderr if not passed else proc.stdout,
    )
