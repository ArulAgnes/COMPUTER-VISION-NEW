"use client";

import { useEffect, useState } from "react";
import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import { api, formatRatio, PublicConfigResponse } from "@/lib/api";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; config: PublicConfigResponse }
  | { kind: "error"; message: string };

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-800 py-2 last:border-b-0">
      <span className="text-sm text-slate-400">{label}</span>
      <span className="font-mono text-sm text-slate-200">{value}</span>
    </div>
  );
}

/** Settings page — renders the real configuration loaded by the backend. */
export default function SettingsPage() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    api
      .config()
      .then((config) => {
        if (!cancelled) setState({ kind: "ready", config });
      })
      .catch((error: Error) => {
        if (!cancelled) setState({ kind: "error", message: error.message });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Configuration loaded from configs/project.yaml. These are settings, not results."
        stage="Stage 1"
      />

      {state.kind === "loading" && <p className="text-sm text-slate-500">Loading configuration…</p>}

      {state.kind === "error" && (
        <div className="rounded-lg border border-amber-700/60 bg-amber-950/40 p-4">
          <p className="text-sm font-medium text-amber-300">Backend not reachable</p>
          <p className="mt-1 text-sm text-amber-400/80">{state.message}</p>
        </div>
      )}

      {state.kind === "ready" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-5">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
              Project
            </h2>
            <Row label="Name" value={state.config.project_name} />
            <Row label="Version" value={state.config.project_version} />
            <Row label="Image size" value={`${state.config.image_size} px`} />
            <Row label="Classes (num_classes)" value={String(state.config.num_classes)} />
          </section>

          <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-5">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
              Classes
            </h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="pb-2">ID</th>
                  <th className="pb-2">Name</th>
                </tr>
              </thead>
              <tbody className="font-mono text-slate-200">
                {state.config.classes.map((cls) => (
                  <tr key={cls.id} className="border-t border-slate-800">
                    <td className="py-2">{cls.id}</td>
                    <td className="py-2">{cls.name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-5">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
              Dataset Split
            </h2>
            <Row label="Train" value={formatRatio(state.config.split.train_ratio)} />
            <Row label="Validation" value={formatRatio(state.config.split.validation_ratio)} />
            <Row label="Test" value={formatRatio(state.config.split.test_ratio)} />
            <Row label="Seed" value={String(state.config.split.seed)} />
            <Row label="Stratified" value={state.config.split.stratified ? "yes" : "no"} />
          </section>

          <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-5">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
              Thresholds
            </h2>
            <Row label="Confidence" value={state.config.thresholds.confidence.toFixed(2)} />
            <Row label="NMS" value={state.config.thresholds.nms.toFixed(2)} />
            <Row label="IoU" value={state.config.thresholds.iou.toFixed(2)} />
            <Row
              label="Evaluation IoU"
              value={state.config.evaluation.iou_threshold.toFixed(2)}
            />
          </section>

          <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-5">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
              Training (from scratch)
            </h2>
            <Row label="Epochs" value={String(state.config.training.epochs)} />
            <Row label="Batch size" value={String(state.config.training.batch_size)} />
            <Row label="Learning rate" value={String(state.config.training.learning_rate)} />
            <Row label="Seed" value={String(state.config.training.seed)} />
            <Row label="Pretrained weights" value="not used (random init)" />
          </section>

          <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-5">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
              Evaluation Targets
            </h2>
            <div className="mb-3 rounded-md border border-slate-800 bg-slate-950 p-3">
              <p className="text-xs text-slate-500">
                Targets below are GOALS configured for evaluation — they are not achieved
                results.
              </p>
            </div>
            <Row
              label="Target mAP"
              value={
                state.config.evaluation.target_map !== null
                  ? state.config.evaluation.target_map.toFixed(2)
                  : "Not available"
              }
            />
            <Row
              label="Target F1"
              value={
                state.config.evaluation.target_f1 !== null
                  ? state.config.evaluation.target_f1.toFixed(2)
                  : "Not available"
              }
            />
          </section>

          <div className="lg:col-span-2">
            <EmptyState
              title="Environment-specific overrides"
              message="Genuine environment values are provided via environment variables (CV_CONFIG, CV_PROJECT_ROOT, CV_RAW_DATA_DIR) — see docs/ARCHITECTURE.md."
            />
          </div>
        </div>
      )}
    </div>
  );
}
