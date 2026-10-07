/**
 * Typed API client for the FastAPI backend.
 * Every type mirrors an apps/api response schema.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  classes: string[];
};

export type Stage0Baseline = {
  source: string | null;
  stage: string | null;
  audited_at: string | null;
  total_images: number | null;
  class_counts: Record<string, number> | null;
};

export type EvaluationStatus = {
  status: string;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  map: number | null;
};

export type PipelineStatus = {
  dataset_version: string | null;
  annotated_images: number | null;
  train_images: number | null;
  validation_images: number | null;
  test_images: number | null;
  model_version: string | null;
  evaluation: EvaluationStatus;
};

export type StatusResponse = {
  stage0_baseline: Stage0Baseline | null;
  pipeline: PipelineStatus;
};

export type PublicConfigResponse = {
  project_name: string;
  project_version: string;
  classes: { id: number; name: string }[];
  num_classes: number;
  image_size: number;
  split: {
    train_ratio: number;
    validation_ratio: number;
    test_ratio: number;
    seed: number;
    stratified: boolean;
  };
  thresholds: { confidence: number; nms: number; iou: number };
  evaluation: { iou_threshold: number; target_map: number | null; target_f1: number | null };
  training: { epochs: number; batch_size: number; learning_rate: number; seed: number };
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  return parseResponse<T>(response, path);
}

async function postJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { method: "POST" });
  return parseResponse<T>(response, path);
}

/** Parses a response, surfacing the backend's standard error envelope. */
async function parseResponse<T>(response: Response, path: string): Promise<T> {
  if (!response.ok) {
    let code = "HTTP_" + response.status;
    let message = `${path} returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as {
        error?: { code?: string; message?: string };
        detail?: string;
      };
      if (body.error?.code) code = body.error.code;
      if (body.error?.message) message = body.error.message;
      else if (body.detail) message = String(body.detail);
    } catch {
      // non-JSON error body: keep defaults
    }
    throw new ApiError(response.status, code, message);
  }
  return (await response.json()) as T;
}

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

/** True when the dataset has not been scanned yet (not an outage). */
export function isNotScanned(error: unknown): boolean {
  return error instanceof ApiError && error.code === "DATASET_NOT_SCANNED";
}

// ---------------------------------------------------------------------------
// Stage 2: dataset discovery + image quality
// ---------------------------------------------------------------------------

export type ManifestSummary = {
  total_images: number;
  readable: number;
  unreadable: number;
  class_counts: Record<string, number>;
  unknown_class: number;
  no_class: number;
  format_counts: Record<string, number>;
  dimension_counts: Record<string, number>;
  exact_duplicate_images: number;
  exact_duplicate_groups: number;
  suspicious_duplicate_images: number;
  suspicious_duplicate_pairs: number;
  grayscale_images: number;
  color_images: number;
  total_bytes: number;
};

export type QualitySummary = {
  total: number;
  pass_count: number;
  review_count: number;
  fail_count: number;
  flagged_count: number;
  flag_counts: Record<string, number>;
  blur_statistics: Record<string, number | null>;
  brightness_statistics: Record<string, number | null>;
  blur_distribution: Record<string, number>;
  brightness_distribution: Record<string, number>;
  resolution_distribution: Record<string, number>;
  low_resolution_count: number;
  exact_duplicate_images: number;
  suspicious_duplicate_images: number;
};

export type DatasetSummaryResponse = {
  generated_at: string;
  source: string;
  classes: { id: number; name: string }[];
  summary: ManifestSummary;
  suspicious_duplicate_pairs: {
    image_id_a: string;
    image_id_b: string;
    path_a: string;
    path_b: string;
    hamming_distance: number;
    method: string;
  }[];
};

export type ImageListItem = {
  image_id: string;
  filename: string;
  source_relative_path: string;
  class_name: string | null;
  class_id: number | null;
  width: number | null;
  height: number | null;
  channels: number | null;
  color_mode: string | null;
  file_size_bytes: number;
  extension: string;
  readable: boolean;
  status: string;
  is_exact_duplicate: boolean;
  duplicate_group_id: string | null;
  is_suspicious_duplicate: boolean;
  quality_status: string | null;
  flags: string[];
};

export type ImageListResponse = {
  items: ImageListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type QualityRecord = {
  image_id: string;
  source_relative_path: string;
  class_name: string | null;
  quality_status: string;
  flags: string[];
  width: number | null;
  height: number | null;
  blur_score: number | null;
  brightness_mean: number | null;
  aspect_ratio: number | null;
  file_size_kb: number;
  sha256: string;
  is_exact_duplicate: boolean;
  duplicate_group_id: string | null;
  is_suspicious_duplicate: boolean;
};

export type QualityResponse = {
  generated_at: string;
  thresholds: Record<string, unknown> & {
    note?: string;
    blur_review_threshold?: number;
    blur_fail_threshold?: number;
    brightness_dark_threshold?: number;
    brightness_bright_threshold?: number;
    min_width?: number;
    min_height?: number;
    aspect_ratio_min?: number;
    aspect_ratio_max?: number;
    blur_method?: string;
  };
  near_duplicate_method: string | null;
  summary: QualitySummary;
  flagged_records: QualityRecord[];
};

export type ScanResponse = {
  success: boolean;
  duration_seconds: number;
  image_count: number;
  summary: ManifestSummary;
  quality_summary: QualitySummary;
  outputs: Record<string, string>;
};

export type ImageQuery = {
  page?: number;
  page_size?: number;
  class_name?: string | null;
  quality_status?: string | null;
};

function queryString(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export const api = {
  health: () => getJson<HealthResponse>("/api/health"),
  status: () => getJson<StatusResponse>("/api/status"),
  config: () => getJson<PublicConfigResponse>("/api/config"),

  datasetSummary: () => getJson<DatasetSummaryResponse>("/api/dataset/summary"),
  datasetImages: (query: ImageQuery) =>
    getJson<ImageListResponse>(`/api/dataset/images${queryString(query)}`),
  datasetImage: (imageId: string) =>
    getJson<{ record: Record<string, unknown>; quality: QualityRecord | null }>(
      `/api/dataset/images/${imageId}`,
    ),
  datasetQuality: () => getJson<QualityResponse>("/api/dataset/quality"),
  scanDataset: () => postJson<ScanResponse>("/api/dataset/scan"),
  thumbnailUrl: (imageId: string, size = 128) =>
    `${API_BASE}/api/dataset/images/${imageId}/thumbnail${queryString({ size })}`,
};

/** Renders a possibly-absent value the honest way. */
export function valueOrNA(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }
  return String(value);
}

export function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Not available";
  }
  return value.toFixed(3);
}

export function formatRatio(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

/** Human-readable file size from a measured byte count. */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}
