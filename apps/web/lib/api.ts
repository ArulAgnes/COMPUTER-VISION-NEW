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
  if (!response.ok) {
    throw new Error(`${path} returned HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => getJson<HealthResponse>("/api/health"),
  status: () => getJson<StatusResponse>("/api/status"),
  config: () => getJson<PublicConfigResponse>("/api/config"),
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
