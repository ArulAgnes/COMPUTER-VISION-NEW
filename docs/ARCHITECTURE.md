# Architecture

**Stage 1 baseline.** This document describes the structure of
Computer Vision New and the conventions later stages must follow.

## Overview

```text
┌──────────────────────┐        HTTP (JSON)        ┌──────────────────────┐
│  apps/web            │ ────────────────────────► │  apps/api            │
│  Next.js dashboard   │  /api/health              │  FastAPI             │
│  React + TS + TW4    │  /api/config              │  config / status /   │
│                      │  /api/status              │  future pipeline ops │
└──────────────────────┘                           └──────────┬───────────┘
                                                              │ imports
                                                   ┌──────────▼───────────┐
                                                   │  ai/  packages       │
                                                   │  dataset, annotation │
                                                   │  model, training …   │
                                                   └──────────┬───────────┘
                                    reads (never writes)      │ writes
                     ┌──────────────────────┐        ┌────────▼────────────┐
                     │ RAW DATA (external)  │        │ GENERATED (in repo) │
                     │ captured_photos\     │        │ data/, models/,     │
                     │  bell, oillamp       │        │ logs/               │
                     └──────────────────────┘        └─────────────────────┘
```

## Frontend — `apps/web`

- Next.js (App Router), React, TypeScript, Tailwind CSS 4.
- Shared shell: `app/layout.tsx` renders the sidebar (`components/Sidebar.tsx`)
  and the main content area.
- Navigation is centralized in `lib/navigation.ts` — adding a section means
  adding one entry there.
- `app/page.tsx` (Dashboard) and `app/settings/page.tsx` are client components
  that fetch real data from the API; unknown sections fall through to
  `app/[section]/page.tsx` (server component, real HTTP 404 via `notFound()`).
- `lib/api.ts` holds the typed API client and the honest formatting helpers
  (`valueOrNA`, `formatMetric`): `null` renders as **Not available**.
- UI conventions: dark professional theme, no decorative animations, no invented
  numbers, empty states are explicit.

## Backend — `apps/api`

```text
apps/api/
├── app/
│   ├── main.py            application factory (create_app), lifespan, error handlers
│   ├── api/routes/        health.py, config.py, status.py (+ later routes)
│   ├── core/
│   │   ├── config.py      YAML loading + validation (pydantic), env overrides
│   │   ├── paths.py       path resolution + RAW-DATA write protection
│   │   └── logging.py     structured logging (stdout + logs/api.log)
│   ├── schemas/           response models (health, config, status, common errors)
│   └── services/          status_service.py (+ later pipeline services)
└── tests/                 pytest suite (TestClient)
```

Run: `python -m uvicorn app.main:app --app-dir apps/api --reload`

### Error contract

Failures return a standard envelope:

```json
{ "success": false, "error": { "code": "RAW_DATA_WRITE_VIOLATION", "message": "..." } }
```

### Existing endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Real service status (name, version, configured classes) |
| `GET /api/config` | Public configuration (classes, split, thresholds, targets) |
| `GET /api/status` | Dashboard status: Stage 0 baseline + pipeline values (`null` until produced) |

Later stages add: dataset scan/quality, annotations, split, augmentation,
dataset versions, training, evaluation, errors/diagnosis/recommendations,
inference.

## AI modules — `ai/`

Placeholder packages exist for the full pipeline; each gains real code in its
stage:

| Package | Stage | Responsibility |
|---|---|---|
| `ai/dataset` | 2, 4, 5+ | discovery, manifest, split, versioning |
| `ai/annotation` | 3 | annotation storage, conversion, validation |
| `ai/augmentation` | 5 | train-only augmentation with bbox transforms |
| `ai/model` | 6 | custom detector, **random initialization** |
| `ai/training` | 7 | from-scratch training engine, checkpoints |
| `ai/evaluation` | 8 | IoU, precision, recall, F1, AP, mAP, confusion matrix |
| `ai/diagnostics` | 9 | error analysis, data diagnosis, recommendations |
| `ai/inference` | 10 | image + camera inference, NMS |

### Model policy (mandatory)

The detector uses **random initialization only**:

- no pretrained YOLO/ImageNet/COCO weights,
- no transfer learning, no pretrained backbones, no foundation models,
- training must fail if a pretrained weight is configured (safety check in Stage 7),
- checkpoint metadata records `pretrained = false`, `transfer_learning = false`,
  `initialization = random`.

External libraries (PyTorch, OpenCV, NumPy, Pillow) are allowed for tensor ops,
image processing and training utilities — the weights themselves start random.

## Configuration — `configs/`

`configs/project.yaml` is the single source of truth:

- `classes` (id + name) — `num_classes` is always derived, never hardcoded
- `paths` — raw data dir (read-only) + generated dirs (relative to repo root)
- `image.size`, `split` (ratios, seed, stratified), `training`, `thresholds`
- `evaluation.iou_threshold` and `evaluation.targets` (goals, not results)
- `quality` thresholds (Stage 2), `augmentation` (Stage 5)

Environment variables are used only for genuine environment differences:

| Variable | Purpose |
|---|---|
| `CV_CONFIG` | alternative config file path |
| `CV_PROJECT_ROOT` | project root override |
| `CV_RAW_DATA_DIR` | raw dataset directory override |
| `NEXT_PUBLIC_API_BASE` | frontend API base URL |

## Data flow

```text
RAW (read-only)                 GENERATED (inside repository)
captured_photos\   ──scan──►    data/manifests/      image manifest
                        │       data/annotations/   bbox annotations
                        │       data/datasets/      split manifests (git-ignored)
                        │       data/augmented/     train-only augmented images
                        │       data/versions/      dataset version records
                        │       data/reports/       generated reports
                        └──►    models/checkpoints/ *.pt checkpoints (git-ignored)
                                models/registry/    model metadata (git-ignored)
                                logs/               runtime logs
```

### Raw vs generated separation

1. `paths.raw_data_dir` points outside the repository and is never written to.
2. `app/core/paths.py::assert_not_raw()` guards every generated path;
   violations raise `RawDataViolationError` → HTTP 403.
3. Tests assert the raw directory is outside the project root and that
   generated directories are distinct from it.
4. `.gitignore` excludes generated datasets, augmented images, checkpoints,
   registry files and logs — source, configs, docs and tests stay tracked.

## Reproducibility

Every major operation (later stages) must record: timestamp, action, dataset
version, model version, random seed, configuration snapshot and software
versions. Seeds come from config (`split.seed`, `training.seed`,
`augmentation.seed`).

## Testing strategy

- `apps/api/tests/` — backend unit/API tests (pytest + TestClient)
- `tests/` — platform-level end-to-end tests (later stages)
- Frontend: ESLint + `next build` (strict TypeScript)
- Stage 0 audit facts live in `configs/stage0_baseline.json` and are compared
  against the API response in tests — no magic numbers in test code.

## Planned API surface (later stages)

```text
POST /api/dataset/scan          GET  /api/dataset            GET /api/dataset/quality
GET/POST/PUT/DELETE /api/annotations...
POST /api/dataset/split         POST /api/dataset/augment
GET  /api/datasets/versions     GET  /api/datasets/versions/{id}
POST /api/training/start        GET  /api/training/{id}
POST /api/evaluation/run        GET  /api/evaluation/{id}
GET  /api/errors                GET  /api/diagnosis          GET /api/recommendations
POST /api/inference             POST /api/inference/camera
```

Naming may be adjusted when implemented, but the error envelope, config
loading, path protection and null-means-not-available conventions stay fixed.
