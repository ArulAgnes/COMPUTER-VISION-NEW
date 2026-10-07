# Computer Vision Data-Centric Platform

**Computer Vision New** is a data-centric, closed-loop computer vision platform.
It is not a collection of disconnected scripts: one integrated pipeline drives
raw images all the way to a trained detector — and then feeds evaluation errors
back into data improvement.

A distinctive data-centric closed-loop approach:

```text
DATA
 ↓
ANNOTATION
 ↓
TRAINING
 ↓
EVALUATION
 ↓
ERROR ANALYSIS
 ↓
DATA DIAGNOSIS
 ↓
DATA RECOMMENDATION
 ↓
IMPROVED DATA
 ↓
NEW DATASET VERSION
 ↓
NEW MODEL
 ↓
INFERENCE
```

The loop's purpose: understand *why* a model fails, translate that into
concrete data problems, recommend what data to collect, and prove that the next
model version is actually better — with real measured metrics only.

## Honesty rules baked into the platform

- No metric is ever fabricated. If a value has not been computed, the UI shows
  **Not available** and the API returns `null`.
- Quality targets (e.g. target mAP 0.95) are *goals*, clearly separated from
  achieved results.
- The detector is trained **from scratch**: random initialization, no pretrained
  weights, no transfer learning, no COCO/ImageNet checkpoints.
- Raw photos are **read-only**; everything generated lives inside this repository.

## Current status — Stage 2

Stages completed:

- **Stage 0** — repository + read-only raw data audit (`docs/DATA_AUDIT.md`):
  26 JPEG images (13 `bell`, 13 `oillamp`), no corrupted files, no duplicates.
- **Stage 1** — architecture + backend/frontend skeleton.
- **Stage 2** — dataset discovery + image quality engine
  (`docs/DATASET_DISCOVERY.md`, `docs/IMAGE_QUALITY.md`): reproducible
  manifest, exact/near duplicate detection, real blur/brightness/resolution
  measurements, dashboard pages (`/dataset`, `/quality`) and the
  `python -m cvplatform` CLI.

Not yet implemented (later stages): annotation, splitting, augmentation,
training, evaluation, error analysis, diagnosis, inference, camera.

No model has been trained and **no evaluation metrics exist yet**.

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Backend | Python 3.11, FastAPI, Pydantic |
| Vision / ML | OpenCV, NumPy, Pillow, PyTorch (from-scratch training) |
| Storage | Filesystem + JSON manifests / metadata (no database required) |
| Tests | pytest, ESLint, TypeScript compiler |

## Repository structure

```text
COMPUTER-VISION-NEW/
├── apps/
│   ├── api/          FastAPI backend (app/main.py, routes, core, schemas, services, tests)
│   └── web/          Next.js dashboard
├── ai/               ML pipeline packages (model, training, evaluation, inference,
│                     augmentation, annotation, dataset, diagnostics)
├── cvplatform/       CLI (python -m cvplatform scan|quality)
├── data/             Generated manifests, annotations, datasets, versions, reports
├── models/           Checkpoints and model registry (generated)
├── scripts/          CLI entry points (later stages)
├── tests/            Platform-level end-to-end tests (later stages)
├── docs/             Architecture and pipeline documentation
├── configs/          project.yaml (single source of configuration)
├── logs/             Runtime logs (git-ignored)
├── requirements.txt
└── pytest.ini
```

## Raw data location (read-only)

```text
D:\IEEE\100%Project\captured_photos\
├── bell\      (13 images)
└── oillamp\   (13 images)
```

This folder lives **outside** the repository and is configured in
`configs/project.yaml` (`paths.raw_data_dir`). The application refuses to write
inside it (`RawDataViolationError` → HTTP 403).

## Development setup

### Backend

```powershell
cd D:\IEEE\100%Project\COMPUTER-VISION-NEW
python -m pip install -r requirements.txt

# run the API
python -m uvicorn app.main:app --app-dir apps/api --reload

# health check
Invoke-RestMethod http://127.0.0.1:8000/api/health

# dataset discovery + quality scan (also: POST /api/dataset/scan, or the UI)
python -m cvplatform scan
```

### Frontend

```powershell
cd D:\IEEE\100%Project\COMPUTER-VISION-NEW\apps\web
npm install
npm run dev        # http://localhost:3000
```

### Tests and checks

```powershell
python -m pytest            # backend tests
python -m ruff check .      # Python lint

cd apps\web
npm run lint                # ESLint
npm run build               # TypeScript + production build
```

The frontend reaches the API at `http://127.0.0.1:8000` (override with
`NEXT_PUBLIC_API_BASE`).

## Planned pipeline

```text
RAW DATA
→ DATASET DISCOVERY
→ IMAGE QUALITY
→ ANNOTATION
→ VALIDATION
→ SPLIT
→ TRAIN-ONLY AUGMENTATION
→ DATASET VERSION
→ FROM-SCRATCH TRAINING
→ EVALUATION
→ ERROR ANALYSIS
→ DATA DIAGNOSIS
→ DATA RECOMMENDATION
→ IMPROVED DATA
→ NEW DATASET VERSION
→ NEW MODEL
→ INFERENCE
```

Each arrow is a real, tested stage — not a diagram. See `docs/ARCHITECTURE.md`
for how the pieces fit together.

## Documentation

- `docs/DATA_AUDIT.md` — Stage 0 baseline audit (measured facts)
- `docs/DATASET_DISCOVERY.md` — Stage 2 manifest, duplicates, reproducibility
- `docs/IMAGE_QUALITY.md` — Stage 2 measurements, flags, thresholds
- `docs/ARCHITECTURE.md` — system architecture and conventions
