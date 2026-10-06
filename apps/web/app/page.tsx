"use client";

import { useEffect, useState } from "react";
import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import StatCard from "@/components/StatCard";
import { api, formatMetric, StatusResponse, valueOrNA } from "@/lib/api";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; status: StatusResponse }
  | { kind: "error"; message: string };

export default function DashboardPage() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    api
      .status()
      .then((status) => {
        if (!cancelled) setState({ kind: "ready", status });
      })
      .catch((error: Error) => {
        if (!cancelled) setState({ kind: "error", message: error.message });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const baseline = state.kind === "ready" ? state.status.stage0_baseline : null;
  const pipeline = state.kind === "ready" ? state.status.pipeline : null;

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Live platform status. Every value comes from real project data or is shown as Not available."
        stage="Stage 1"
      />

      {state.kind === "loading" && (
        <p className="text-sm text-slate-500">Loading platform status…</p>
      )}

      {state.kind === "error" && (
        <div className="mb-6 rounded-lg border border-amber-700/60 bg-amber-950/40 p-4">
          <p className="text-sm font-medium text-amber-300">Backend not reachable</p>
          <p className="mt-1 text-sm text-amber-400/80">
            {state.message}. Start the API with{" "}
            <code className="rounded bg-slate-800 px-1.5 py-0.5 text-amber-200">
              uvicorn app.main:app --app-dir apps/api
            </code>{" "}
            (see README). Values stay hidden until the API responds.
          </p>
        </div>
      )}

      <section className="mb-8">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Stage 0 Raw Dataset Baseline
          </h2>
          <p className="text-xs text-slate-600">
            source: {baseline?.source ?? "Not available"} · audited:{" "}
            {baseline?.audited_at ?? "Not available"}
          </p>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard
            label="Total raw images"
            value={baseline?.total_images ?? null}
            hint="Read-only audit — not a training result"
            emphasis
          />
          {baseline?.class_counts
            ? Object.entries(baseline.class_counts).map(([name, count]) => (
                <StatCard key={name} label={`Raw images · ${name}`} value={count} emphasis />
              ))
            : ["bell", "oillamp"].map((name) => (
                <StatCard key={name} label={`Raw images · ${name}`} value={null} />
              ))}
        </div>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Pipeline
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard label="Dataset version" value={pipeline?.dataset_version ?? null} />
          <StatCard label="Annotated images" value={pipeline?.annotated_images ?? null} />
          <StatCard label="Train images" value={pipeline?.train_images ?? null} />
          <StatCard label="Validation images" value={pipeline?.validation_images ?? null} />
          <StatCard label="Test images" value={pipeline?.test_images ?? null} />
          <StatCard label="Model version" value={pipeline?.model_version ?? null} />
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Evaluation
          </h2>
          <p className="text-xs text-slate-600">
            {pipeline
              ? pipeline.evaluation.status === "not_evaluated_yet"
                ? "Not evaluated yet"
                : pipeline.evaluation.status
              : "Not available"}
          </p>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Precision" value={formatMetric(pipeline?.evaluation.precision)} emphasis />
          <StatCard label="Recall" value={formatMetric(pipeline?.evaluation.recall)} emphasis />
          <StatCard label="F1" value={formatMetric(pipeline?.evaluation.f1)} emphasis />
          <StatCard label="mAP@0.50" value={formatMetric(pipeline?.evaluation.map)} emphasis />
        </div>
        {state.kind === "ready" && (
          <div className="mt-6">
            <EmptyState
              title="No evaluation has been run"
              message="Metrics appear here only after a model is trained and evaluated on the test split. The platform never displays estimated or fabricated numbers."
            />
          </div>
        )}
      </section>

      <p className="mt-8 text-xs text-slate-600">
        Latest evaluation: {valueOrNA(pipeline?.evaluation.status)}
      </p>
    </div>
  );
}
