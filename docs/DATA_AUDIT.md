# Stage 0 — Repository & Raw Data Audit (Baseline Report)

**Date:** 2026-10-06
**Stage:** STAGE 0 — Repository + raw data audit
**Status:** Complete (read-only; no raw data modified)

---

## 1. Repository Verification

| Check | Result |
|---|---|
| Working directory before clone | `D:\IEEE\100%Project` (not a git repository) |
| Target local path | `D:\IEEE\100%Project\COMPUTER-VISION-NEW` |
| Remote | `https://github.com/ArulAgnes/COMPUTER-VISION-NEW.git` |
| Clone result | Cloned successfully (repository was empty — no commits) |
| Branch | `main` |
| Commits at clone time | none (empty repository) |
| Tooling available | git 2.54.0, Python 3.11.9, Pillow 11.3.0, OpenCV 5.0.0, NumPy 2.4.6 |

The repository matches the required identity `ArulAgnes/COMPUTER-VISION-NEW`. No other repository was used or inspected.

---

## 2. Raw Data Location

```text
D:\IEEE\100%Project\captured_photos\
├── bell\      (13 images)
└── oillamp\   (13 images)
```

The raw folder was opened **read-only**. No file was renamed, resized, overwritten, deleted, or augmented.

---

## 3. Inventory

| Metric | Value |
|---|---|
| Total image files | 26 |
| `bell` images | 13 |
| `oillamp` images | 13 |
| Class balance | 13 / 13 (balanced) |
| File format | `.jpeg` (26/26), decoded as JPEG |
| Color mode | RGB (26/26), none grayscale |
| Corrupted images | 0 |
| Unreadable files | 0 |
| Unsupported extensions | 0 |
| Exact duplicates (SHA-256) | 0 groups |
| Suspicious duplicates (16×16 perceptual hash, Hamming ≤ 6) | 0 pairs |

### Dimensions

| Resolution | Count |
|---|---|
| 960×1280 | 22 |
| 1200×1600 | 2 (bell) |
| 1232×1600 | 1 (bell) |
| 1280×960 | 1 (bell, landscape) |

All `oillamp` images are 960×1280 portrait. `bell` contains four images at other resolutions (three portrait, one landscape).

### File sizes

| Class | Min | Median | Max |
|---|---|---|---|
| bell | 51 KB | 68 KB | 165 KB |
| oillamp | 87 KB | 151 KB | 267 KB |

---

## 4. Measured Quality Metrics (real computations)

Metrics computed with OpenCV/Pillow on the original files (read-only):

- **Blur score** = variance of the Laplacian on the grayscale image.
- **Brightness** = mean grayscale intensity (0–255).
- **Grayscale check** = mean max per-channel difference (all images are color).

### Per-class statistics

| Metric | bell | oillamp |
|---|---|---|
| Blur min / median / max | 6.83 / 38.59 / 233.19 | 66.85 / 1001.70 / 3297.96 |
| Images with blur < 20 | 5 of 13 | 0 of 13 |
| Images with blur < 50 | 9 of 13 | 0 of 13 |
| Brightness min / median / max | 50.37 / 91.55 / 135.84 | 62.67 / 98.08 / 138.15 |
| Images with brightness < 60 | 1 of 13 | 0 of 13 |
| Images with brightness > 150 | 0 | 0 |

### Baseline observations (facts, not claims)

1. **The `bell` class is noticeably softer/blurrier than `oillamp`.** 5 of 13 bell images have a Laplacian variance below 20 and 9 of 13 are below 50, while every oillamp image is above 66 (median 1001.7). This is a real measured imbalance in sharpness between classes that will affect training and must be surfaced by the quality engine.
2. **No extreme exposure problems found**: all brightness values fall in 50–139 (no image under 40 or over 220 at default thresholds).
3. **No duplicates or near-duplicates** were detected by SHA-256 or perceptual hashing.
4. **Dataset is very small** (26 images total, 2 classes). This is far below what a from-scratch detector needs for strong results. The platform must report this honestly and drive data collection through the diagnosis/recommendation loop.
5. **Aspect ratio is mostly uniform** (one landscape bell image at 1280×960).

### Blur thresholds used in this audit

Reporting only — final thresholds are configurable in Stage 2:

- blur < 20 → potentially blurry (bell: 5 images)
- blur < 50 → soft focus (bell: 9 images)

---

## 5. Dataset Readiness Summary

| Question | Answer |
|---|---|
| Can discovery run? | Yes — all 26 files are valid, decodable images |
| Annotations exist? | No — none present in the raw folder (correct; annotation is Stage 3) |
| Splits exist? | No — Stage 4 |
| Ready for training? | No — annotation, validation, split, and augmentation must happen first |
| Limitation to disclose | 26 images / 2 classes is a small dataset; quality is uneven across classes |

---

## 6. Integrity Note

No writes of any kind were performed inside `D:\IEEE\100%Project\captured_photos`. All analysis used read operations (`os.stat`, `hashlib`, `PIL.Image.open` with `verify()`, `cv2.imread`). Every generated artifact is written only inside `D:\IEEE\100%Project\COMPUTER-VISION-NEW` or a temporary working directory.

---

## 7. Next Stage

**STAGE 1** — Project architecture + backend/frontend skeleton (directory layout, configuration, `.gitignore`, `requirements.txt`, FastAPI app shell, Next.js app shell).
