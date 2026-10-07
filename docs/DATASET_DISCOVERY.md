# Dataset Discovery

**Stage 2.** Real discovery of the read-only raw dataset into a reproducible
manifest. Nothing here is mocked: every value comes from actually opening the
files.

## What discovery does

1. **Walk** `paths.raw_data_dir` recursively (sorted, deterministic) and keep
   files with supported extensions: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`.
   Everything else is ignored (e.g. `Thumbs.db`, `.txt`).
2. **Hash** each file with streaming SHA-256 (content identity).
3. **Decode** each image with Pillow (metadata: size, mode, bands) and OpenCV
   (pixels for quality/duplicates). A corrupted file is recorded as
   `readable: false` with `status: "unreadable"` and a real `decode_error` —
   it never aborts the scan.
4. **Resolve the class** from the first folder of the relative path against
   `configs/project.yaml → classes`. A folder that is not configured becomes
   `status: "unknown_class"` (visible, not silently dropped); a file directly
   in the root becomes `status: "no_class"`.
5. **Detect duplicates** (exact via SHA-256, near via perceptual hash) and
   **measure quality** (see `IMAGE_QUALITY.md`) in the same pass — each image
   is decoded exactly once.

## image_id (deterministic, no UUIDs)

```text
image_id = "img_" + sha256(source_relative_path + "\0" + content_sha256)
```

Same file → same id on every run and on every machine. Exact duplicates in
different folders stay separately addressable because the relative path is
part of the formula; their content identity remains in `sha256`.

## Duplicate detection

| Kind | Method | Result |
|---|---|---|
| Exact | identical SHA-256 | `is_exact_duplicate`, shared `duplicate_group_id` (`dup_<sha[:12]>`) |
| Suspicious (near) | 64-bit dHash (difference hash), Hamming distance ≤ `duplicates.near_duplicate.max_hamming_distance` (default 6) | `is_suspicious_duplicate` on both images + a `suspicious_duplicate_pairs` entry with the measured distance |

Exact duplicates are excluded from the near-duplicate pass (they are already
reported). Detection thresholds live in `configs/project.yaml → duplicates`.

## Outputs

| File | Content |
|---|---|
| `data/manifests/dataset_manifest.json` | Full records, summary, suspicious pairs, schema version, timestamp (git-ignored) |
| `data/manifests/dataset_manifest.csv` | Same records, flat columns for spreadsheets (git-ignored) |

Every record contains: `image_id`, `source_relative_path`, `class_name`,
`class_id`, `filename`, `extension`, `width`, `height`, `channels`,
`color_mode`, `file_size_bytes`, `sha256`, `perceptual_hash`, `readable`,
`decode_error`, `status`, `is_exact_duplicate`, `duplicate_group_id`,
`is_suspicious_duplicate`, `discovery_timestamp`.

The absolute `source_path` is stored for internal use only and is **never**
returned by the API.

## How to run

```powershell
# CLI (from the repository root)
python -m cvplatform scan

# API
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/dataset/scan

# UI
# http://localhost:3000/dataset  → "Run scan"
```

Exit codes (CLI): `0` success, `2` fatal (missing config, missing raw dataset,
missing manifest for `quality`). Unreadable images are reported in the
summary but do not fail the scan.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/dataset/scan` | Run discovery + quality, write outputs |
| `GET /api/dataset/summary` | Summary counts (404 `DATASET_NOT_SCANNED` before the first scan) |
| `GET /api/dataset/images` | Paginated records; filters `class_name`, `quality_status` |
| `GET /api/dataset/images/{id}` | One record + quality analysis |

## Guarantees

- **Read-only raw data.** Discovery only opens files for reading; tests hash
  all 26 source files before and after a scan and assert the bytes are
  unchanged.
- **Reproducible.** Two scans of the same data produce identical records and
  quality results (only wall-clock timestamps differ) — covered by
  `test_dataset_scan.py::test_scan_is_reproducible`.
- **No hardcoded counts.** Engine code never contains `26`/`13`/`13`; tests
  compare measured output against `configs/stage0_baseline.json` (the Stage 0
  audit) instead of magic numbers.
- **Consistent with Stage 0.** The manifest's sizes, hashes and formats match
  `docs/DATA_AUDIT.md`.
