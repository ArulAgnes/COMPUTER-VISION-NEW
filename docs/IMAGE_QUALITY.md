# Image Quality Analysis

**Stage 2.** Real pixel measurements per image, plus *configurable
heuristic* flags and an overall PASS / REVIEW / FAIL status. Measurements are
facts; the thresholds that turn them into flags are opinions you can change in
`configs/project.yaml`.

## Measurements (actual calculations)

| Metric | How it is computed |
|---|---|
| `blur_score` | Variance of the Laplacian on the grayscale image (`cv2.Laplacian(gray, CV_64F).var()`) |
| `brightness_mean` / `_std` / `_min` / `_max` | Statistics of grayscale intensity (0–255) |
| `aspect_ratio` | `width / height` |
| `width`, `height`, `pixel_count`, `min_dimension` | From the decoded image |
| `file_size_bytes` / `_kb` / `_mb` | Actual file size on disk |

Unreadable images have `null` metrics — reported as **Not available**, never
as `0`.

### Consistency with Stage 0

The blur and brightness methodology is deliberately identical to the Stage 0
audit (`docs/DATA_AUDIT.md`). A per-image comparison against the Stage 0
baseline showed **0 mismatches** (max relative blur difference 0.0000%, max
brightness difference 0.000), so quality trends remain comparable across
stages.

## Flags (heuristics — configurable)

Derived from the measurements and duplicate status:

| Flag | Condition | Severity (default) |
|---|---|---|
| `decode_failed` | image could not be decoded | FAIL |
| `blur_fail` | `blur_score < quality.blur.fail_threshold` (15.0) | FAIL |
| `blur_review` | `fail ≤ blur_score < quality.blur.review_threshold` (60.0) | REVIEW |
| `low_resolution` | `width < 128` or `height < 128` | REVIEW |
| `too_dark` | `brightness_mean < 45.0` | REVIEW |
| `too_bright` | `brightness_mean > 210.0` | REVIEW |
| `extreme_aspect_ratio` | outside `0.4 – 2.5` | REVIEW |
| `exact_duplicate` | shares SHA-256 with another image | REVIEW |
| `suspicious_duplicate` | near-duplicate pair found | REVIEW |

**Status rule:** any FAIL-severity flag → `FAIL`; else any REVIEW-severity
flag → `REVIEW`; else `PASS`. The severity lists are configuration
(`quality.status_rules`), not code.

## Thresholds

All in `configs/project.yaml → quality`:

```yaml
quality:
  min_width: 128
  min_height: 128
  blur:      { method: laplacian_variance, review_threshold: 60.0, fail_threshold: 15.0 }
  brightness:{ dark_threshold: 45.0, bright_threshold: 210.0 }
  aspect_ratio: { min: 0.4, max: 2.5 }
  status_rules:
    fail_flags:  [decode_failed, blur_fail]
    review_flags: [blur_review, low_resolution, too_dark, too_bright,
                   extreme_aspect_ratio, exact_duplicate, suspicious_duplicate]
```

The exact thresholds used for a run are copied into the report
(`quality_report.json → thresholds`), so a report is always interpretable
later. These are heuristics — a `FAIL` means "review this image against the
configured rules", not "this image is objectively bad".

## Outputs

| File | Content |
|---|---|
| `data/reports/quality_report.json` | Summary, flagged records, all records, applied thresholds (git-ignored) |
| `data/reports/quality_report.csv` | Flat columns for spreadsheets (git-ignored) |

The summary contains real distributions: blur buckets
(fail / review / pass), brightness buckets (dark / normal / bright),
resolution histogram, and min/median/mean/max statistics for blur and
brightness.

## How to run

```powershell
# full scan (discovery + quality)
python -m cvplatform scan

# quality only, reusing an existing manifest (re-reads the images)
python -m cvplatform quality

# API
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/dataset/scan
Invoke-RestMethod http://127.0.0.1:8000/api/dataset/quality

# UI: http://localhost:3000/quality
```

`GET /api/dataset/quality` returns `404 DATASET_NOT_SCANNED` before the first
scan; the UI then shows an explicit empty state (no invented numbers).

## Honesty rules

- Every number in the report was computed from actual pixels in this run.
- `null` metrics (unreadable images) render as **Not available**.
- PASS / REVIEW / FAIL are heuristic classifications under the configured
  thresholds — they are reported together with those thresholds, never
  presented as ground truth.
- Counts are always derived at runtime; nothing is hardcoded in engine code.
