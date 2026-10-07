"""CLI tests via subprocess: real scans, exit codes 0/2, printed summaries."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app.core.config import project_root

REPO_ROOT = project_root()


def run_cli(*args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "cvplatform", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_scan_command_succeeds_and_prints_real_summary(stage0_baseline: dict) -> None:
    result = run_cli("scan")
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert f"Scanned {stage0_baseline['total_images']} images" in out
    assert "bell=13" in out or f"bell={stage0_baseline['class_counts']['bell']}" in out
    assert "PASS=" in out and "REVIEW=" in out and "FAIL=" in out
    assert "dataset_manifest.json" in out
    assert "error" not in out.lower()

    assert (REPO_ROOT / "data" / "manifests" / "dataset_manifest.json").is_file()
    assert (REPO_ROOT / "data" / "reports" / "quality_report.json").is_file()


def test_quality_command_reuses_manifest(stage0_baseline: dict) -> None:
    run_cli("scan")  # ensure the manifest exists
    result = run_cli("quality")
    assert result.returncode == 0, result.stderr
    assert f"{stage0_baseline['total_images']} images" in result.stdout
    assert "PASS=" in result.stdout


def test_missing_config_exits_2(tmp_path: Path) -> None:
    result = run_cli("scan", env_extra={"CV_CONFIG": str(tmp_path / "nope.yaml")})
    assert result.returncode == 2
    assert "error:" in result.stderr


def test_missing_raw_dataset_exits_2(tmp_path: Path) -> None:
    result = run_cli("scan", env_extra={"CV_RAW_DATA_DIR": str(tmp_path / "absent")})
    assert result.returncode == 2
    assert "error:" in result.stderr


def test_unknown_command_exits_2() -> None:
    result = run_cli("frobnicate")
    assert result.returncode == 2  # argparse usage error


def test_help_lists_commands() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    assert "scan" in result.stdout
    assert "quality" in result.stdout
