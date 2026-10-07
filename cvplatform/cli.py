"""cvplatform CLI: dataset discovery and image quality commands.

Usage (from the repository root):

    python -m cvplatform scan      # discovery + quality analysis, writes outputs
    python -m cvplatform quality   # recompute quality from an existing manifest

Exit codes: 0 = success, 2 = fatal error (missing config, missing raw dataset,
missing manifest, or an unexpected failure). Unreadable images are reported in
the summary but never abort a scan.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_API_DIR = REPO_ROOT / "apps" / "api"

# The shared config loader lives in the API package; reuse it so the CLI and
# the API always read the same configs/project.yaml.
for _path in (str(_API_DIR), str(REPO_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from ai.dataset.models import QualityReport  # noqa: E402
from ai.dataset.scan import ScanResult, run_scan  # noqa: E402
from app.core.config import Settings, load_settings  # noqa: E402
from app.services import dataset_service  # noqa: E402


def _print_quality_lines(report: QualityReport) -> None:
    summary = report.summary
    print(
        f"  quality: PASS={summary.pass_count} REVIEW={summary.review_count} FAIL={summary.fail_count}"
    )
    if summary.flag_counts:
        flags = ", ".join(f"{name}={count}" for name, count in summary.flag_counts.items())
        print(f"  flags: {flags}")


def _print_scan_result(result: ScanResult) -> None:
    summary = result.manifest.summary
    print(f"Scanned {summary.total_images} images from {result.manifest.source}")
    classes = ", ".join(f"{name}={count}" for name, count in summary.class_counts.items())
    print(f"  classes: {classes if classes else 'none matched a configured class'}")
    print(f"  readable: {summary.readable} | unreadable: {summary.unreadable}")
    print(
        "  duplicates: "
        f"exact={summary.exact_duplicate_images} in {summary.exact_duplicate_groups} group(s), "
        f"suspicious_pairs={summary.suspicious_duplicate_pairs}"
    )
    _print_quality_lines(result.quality)
    print(
        "  outputs: "
        f"{result.manifest_json_path}, {result.manifest_csv_path}, "
        f"{result.quality_json_path}, {result.quality_csv_path}"
    )
    print(f"  duration: {result.duration_seconds}s")


def _load_settings_or_exit() -> Settings | None:
    try:
        return load_settings()
    except Exception as exc:  # config missing/invalid: fatal, reported cleanly
        print(f"error: failed to load configuration: {exc}", file=sys.stderr)
        return None


def cmd_scan(_args: argparse.Namespace) -> int:
    settings = _load_settings_or_exit()
    if settings is None:
        return 2
    try:
        raw_dir = Path(settings.paths.raw_data_dir).expanduser().resolve()
        if not raw_dir.is_dir():
            raise FileNotFoundError(f"raw dataset directory not found: {raw_dir}")

        result = run_scan(
            raw_dir=raw_dir,
            classes=settings.class_defs(),
            quality_settings=settings.quality,
            duplicate_settings=settings.duplicates,
            manifests_dir=REPO_ROOT / settings.paths.manifests_dir,
            reports_dir=REPO_ROOT / settings.paths.reports_dir,
        )
    except Exception as exc:
        print(f"error: scan failed: {exc}", file=sys.stderr)
        return 2
    _print_scan_result(result)
    return 0


def cmd_quality(_args: argparse.Namespace) -> int:
    settings = _load_settings_or_exit()
    if settings is None:
        return 2
    try:
        if not dataset_service.manifest_exists():
            raise FileNotFoundError(
                "dataset manifest not found — run `python -m cvplatform scan` first"
            )
        report = dataset_service.rerun_quality_only()
    except Exception as exc:
        print(f"error: quality analysis failed: {exc}", file=sys.stderr)
        return 2
    print(f"Quality analysis for {report.summary.total} images (from existing manifest)")
    _print_quality_lines(report)
    print(f"  outputs: {dataset_service.dataset_output_paths()['quality_json']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cvplatform",
        description="Data engine CLI for the Computer Vision New platform.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser(
        "scan", help="discover the dataset and run quality analysis (writes outputs)"
    )
    scan_parser.set_defaults(func=cmd_scan)

    quality_parser = subparsers.add_parser(
        "quality", help="recompute the quality report from an existing manifest"
    )
    quality_parser.set_defaults(func=cmd_quality)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
