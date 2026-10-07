"use client";

import { useCallback, useEffect, useState } from "react";
import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import QualityBadge from "@/components/QualityBadge";
import StatCard from "@/components/StatCard";
import { api, isNotScanned, QualityRecord, QualityResponse } from "@/lib/api";

type Phase = "loading" | "not-scanned" | "error" | "ready";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function Distribution({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data);
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-5">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
        {title}
      </h2>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-500">Not available</p>
      ) : (
        <ul className="space-y-1.5">
          {entries.map(([label, count]) => (
            <li key={label} className="flex items-center justify-between text-sm">
              <span className="text-slate-400">{label}</span>
              <span className="font-mono text-slate-200">{count}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function StatsTable({ title, stats }: { title: string; stats: Record<string, number | null> }) {
  const entries = Object.entries(stats);
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-5">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
        {title}
      </h2>
      <ul className="space-y-1.5">
        {entries.map(([label, value]) => (
          <li key={label} className="flex items-center justify-between text-sm">
            <span className="text-slate-400">{label}</span>
            <span className="font-mono text-slate-200">
              {value === null ? "Not available" : value}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Quality page — measured blur/brightness/duplicate results from Stage 2. */
export default function QualityPage() {
  const [phase, setPhase] = useState<Phase>("loading");
  const [report, setReport] = useState<QualityResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [scanning, setScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let cancelled = false;
    api
      .datasetQuality()
      .then((data) => {
        if (!cancelled) {
          setReport(data);
          setPhase("ready");
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (isNotScanned(err)) {
          setPhase("not-scanned");
        } else {
          setError(errorMessage(err));
          setPhase("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const runScan = useCallback(async () => {
    setScanning(true);
    setScanMessage("");
    try {
      const result = await api.scanDataset();
      setScanMessage(
        `Scan completed in ${result.duration_seconds}s — ${result.image_count} images analyzed.`,
      );
      setRefresh((value) => value + 1);
    } catch (err: unknown) {
      setScanMessage(`Scan failed: ${errorMessage(err)}`);
    } finally {
      setScanning(false);
    }
  }, []);

  const thresholds = report?.thresholds;

  return (
    <div>
      <PageHeader
        title="Image Quality"
        description="Measured quality analysis: Laplacian blur, mean brightness, resolution and duplicate detection. Thresholds shown are configurable heuristics, not ground truth."
        stage="Stage 2"
      />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={runScan}
          disabled={scanning}
          className="rounded-md border border-sky-700 bg-sky-950/70 px-4 py-2 text-sm font-medium text-sky-300 transition hover:bg-sky-900/70 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {scanning ? "Scanning…" : "Run scan"}
        </button>
        {scanMessage && <p className="text-sm text-slate-400">{scanMessage}</p>}
        {report && <p className="ml-auto text-xs text-slate-500">Analyzed at {report.generated_at}</p>}
      </div>

      {phase === "loading" && <p className="text-sm text-slate-500">Loading quality report…</p>}

      {phase === "error" && (
        <div className="rounded-lg border border-amber-700/60 bg-amber-950/40 p-4">
          <p className="text-sm font-medium text-amber-300">Backend not reachable</p>
          <p className="mt-1 text-sm text-amber-400/80">{error}</p>
        </div>
      )}

      {phase === "not-scanned" && (
        <EmptyState
          title="Quality analysis not available yet"
          message="No quality report exists yet. Press “Run scan” (or run `python -m cvplatform scan`) to compute real measurements. Values appear only after a real analysis."
        />
      )}

      {phase === "ready" && report && (
        <div>
          <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="PASS"
              value={report.summary.pass_count}
              emphasis
              hint="no quality flags"
            />
            <StatCard label="REVIEW" value={report.summary.review_count} hint="review flags" />
            <StatCard label="FAIL" value={report.summary.fail_count} hint="fail flags" />
            <StatCard
              label="Flagged total"
              value={report.summary.flagged_count}
              hint={`of ${report.summary.total} images`}
            />
          </div>

          <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Distribution title="Blur distribution" data={report.summary.blur_distribution} />
            <Distribution
              title="Brightness distribution"
              data={report.summary.brightness_distribution}
            />
            <StatsTable title="Blur score (Laplacian variance)" stats={report.summary.blur_statistics} />
          </div>

          <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <StatsTable
              title="Brightness (mean grayscale)"
              stats={report.summary.brightness_statistics}
            />
            <Distribution
              title="Resolution distribution"
              data={report.summary.resolution_distribution}
            />
            <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-5">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
                Thresholds applied
              </h2>
              {thresholds ? (
                <ul className="space-y-1.5 text-sm">
                  <li className="flex justify-between">
                    <span className="text-slate-400">Blur review / fail</span>
                    <span className="font-mono text-slate-200">
                      {String(thresholds.blur_review_threshold)} / {String(thresholds.blur_fail_threshold)}
                    </span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-slate-400">Brightness dark / bright</span>
                    <span className="font-mono text-slate-200">
                      {String(thresholds.brightness_dark_threshold)} /{" "}
                      {String(thresholds.brightness_bright_threshold)}
                    </span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-slate-400">Min width × height</span>
                    <span className="font-mono text-slate-200">
                      {String(thresholds.min_width)} × {String(thresholds.min_height)}
                    </span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-slate-400">Aspect ratio range</span>
                    <span className="font-mono text-slate-200">
                      {String(thresholds.aspect_ratio_min)} – {String(thresholds.aspect_ratio_max)}
                    </span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-slate-400">Blur method</span>
                    <span className="font-mono text-slate-200">
                      {String(thresholds.blur_method)}
                    </span>
                  </li>
                </ul>
              ) : (
                <p className="text-sm text-slate-500">Not available</p>
              )}
              <p className="mt-3 text-xs text-slate-500">
                {typeof thresholds?.note === "string" ? thresholds.note : ""}
              </p>
            </section>
          </div>

          <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-5">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
              Flagged images ({report.flagged_records.length})
            </h2>
            {report.flagged_records.length === 0 ? (
              <p className="text-sm text-slate-500">
                No images were flagged by the configured thresholds.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wider text-slate-500">
                      <th className="pb-2">Image</th>
                      <th className="pb-2">Status</th>
                      <th className="pb-2">Flags</th>
                      <th className="pb-2 text-right">Blur</th>
                      <th className="pb-2 text-right">Brightness</th>
                      <th className="pb-2 text-right">Size</th>
                    </tr>
                  </thead>
                  <tbody className="text-slate-300">
                    {report.flagged_records.map((record: QualityRecord) => (
                      <tr key={record.image_id} className="border-t border-slate-800">
                        <td className="max-w-xs truncate py-2 pr-4" title={record.source_relative_path}>
                          {record.source_relative_path}
                        </td>
                        <td className="py-2 pr-4">
                          <QualityBadge status={record.quality_status} />
                        </td>
                        <td className="py-2 pr-4 text-xs text-slate-500">{record.flags.join(", ")}</td>
                        <td className="py-2 pr-4 text-right font-mono">
                          {record.blur_score === null ? "Not available" : record.blur_score}
                        </td>
                        <td className="py-2 pr-4 text-right font-mono">
                          {record.brightness_mean === null ? "Not available" : record.brightness_mean}
                        </td>
                        <td className="py-2 text-right font-mono">{record.file_size_kb} KB</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
