"use client";

import { useCallback, useEffect, useState } from "react";
import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import QualityBadge from "@/components/QualityBadge";
import StatCard from "@/components/StatCard";
import {
  api,
  formatBytes,
  ImageListItem,
  ImageListResponse,
  isNotScanned,
  DatasetSummaryResponse,
} from "@/lib/api";

const PAGE_SIZE = 24;

type Phase = "loading" | "not-scanned" | "error" | "ready";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** Dataset page — real discovery data from the Stage 2 manifest. */
export default function DatasetPage() {
  const [phase, setPhase] = useState<Phase>("loading");
  const [summary, setSummary] = useState<DatasetSummaryResponse | null>(null);
  const [pageData, setPageData] = useState<ImageListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [classFilter, setClassFilter] = useState("");
  const [qualityFilter, setQualityFilter] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState<string>("");
  const [scanning, setScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    api
      .datasetSummary()
      .then((data) => {
        if (!cancelled) {
          setSummary(data);
          setError("");
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

  useEffect(() => {
    if (!summary) return;
    let cancelled = false;
    api
      .datasetImages({
        page,
        page_size: PAGE_SIZE,
        class_name: classFilter || null,
        quality_status: qualityFilter || null,
      })
      .then((data) => {
        if (!cancelled) {
          setPageData(data);
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
  }, [summary, page, classFilter, qualityFilter, refresh]);

  const runScan = useCallback(async () => {
    setScanning(true);
    setScanMessage("");
    try {
      const result = await api.scanDataset();
      setScanMessage(
        `Scan completed in ${result.duration_seconds}s — ${result.image_count} images analyzed.`,
      );
      setPhase("loading");
      setRefresh((value) => value + 1);
    } catch (err: unknown) {
      setScanMessage(`Scan failed: ${errorMessage(err)}`);
    } finally {
      setScanning(false);
    }
  }, []);

  const totalPages = pageData ? Math.max(1, Math.ceil(pageData.total / PAGE_SIZE)) : 1;
  const rangeStart = pageData && pageData.items.length ? (page - 1) * PAGE_SIZE + 1 : 0;
  const rangeEnd = pageData ? rangeStart + pageData.items.length - 1 : 0;

  return (
    <div>
      <PageHeader
        title="Dataset"
        description="Discovery of the read-only raw dataset: manifest, classes, duplicates and per-image quality status. Run a scan to (re)compute everything from real files."
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
        {summary && (
          <p className="ml-auto text-xs text-slate-500">
            Scanned at {summary.generated_at}
          </p>
        )}
      </div>

      {phase === "loading" && <p className="text-sm text-slate-500">Loading dataset…</p>}

      {phase === "error" && (
        <div className="rounded-lg border border-amber-700/60 bg-amber-950/40 p-4">
          <p className="text-sm font-medium text-amber-300">Backend not reachable</p>
          <p className="mt-1 text-sm text-amber-400/80">{error}</p>
        </div>
      )}

      {phase === "not-scanned" && (
        <div>
          <EmptyState
            title="Dataset not scanned yet"
            message="No manifest exists yet. Press “Run scan” (or run `python -m cvplatform scan`) to discover the raw dataset. Nothing on this page is simulated — values appear only after a real scan."
          />
        </div>
      )}

      {phase === "ready" && summary && pageData && (
        <div>
          <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Total images"
              value={summary.summary.total_images}
              emphasis
              hint={`${summary.summary.unreadable} unreadable`}
            />
            <StatCard
              label="Readable"
              value={summary.summary.readable}
              hint={`${summary.summary.color_images} color / ${summary.summary.grayscale_images} grayscale`}
            />
            <StatCard
              label="Exact duplicates"
              value={summary.summary.exact_duplicate_images}
              hint={`${summary.summary.exact_duplicate_groups} group(s)`}
            />
            <StatCard
              label="Suspicious pairs"
              value={summary.summary.suspicious_duplicate_pairs}
              hint="dHash Hamming distance"
            />
          </div>

          <div className="mb-4 flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-400">
              Class
              <select
                value={classFilter}
                onChange={(event) => {
                  setClassFilter(event.target.value);
                  setPage(1);
                }}
                className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-200"
              >
                <option value="">All classes</option>
                {summary.classes.map((cls) => (
                  <option key={cls.id} value={cls.name}>
                    {cls.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex items-center gap-2 text-sm text-slate-400">
              Quality
              <select
                value={qualityFilter}
                onChange={(event) => {
                  setQualityFilter(event.target.value);
                  setPage(1);
                }}
                className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-200"
              >
                <option value="">All statuses</option>
                <option value="PASS">PASS</option>
                <option value="REVIEW">REVIEW</option>
                <option value="FAIL">FAIL</option>
              </select>
            </label>

            <p className="ml-auto text-xs text-slate-500">
              {pageData.total > 0
                ? `${rangeStart}–${rangeEnd} of ${pageData.total} images`
                : "No images match the current filters"}
            </p>
          </div>

          {pageData.items.length === 0 ? (
            <EmptyState
              title="No images match the current filters"
              message="Change the class or quality filter to see other images from the manifest."
            />
          ) : (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
              {pageData.items.map((item: ImageListItem) => (
                <ImageCard key={item.image_id} item={item} />
              ))}
            </div>
          )}

          <div className="mt-6 flex items-center justify-between">
            <button
              type="button"
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              disabled={page <= 1}
              className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-300 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-xs text-slate-500">
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              disabled={page >= totalPages}
              className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-300 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ImageCard({ item }: { item: ImageListItem }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-900/60">
      <img
        src={api.thumbnailUrl(item.image_id, 256)}
        alt={item.source_relative_path}
        loading="lazy"
        className="h-36 w-full bg-slate-950 object-cover"
      />
      <div className="p-3">
        <p className="truncate text-xs font-medium text-slate-200" title={item.filename}>
          {item.filename}
        </p>
        <p className="mt-0.5 truncate text-[11px] text-slate-500">
          {item.class_name ?? "no class"} ·{" "}
          {item.width && item.height ? `${item.width}×${item.height}` : "size n/a"} ·{" "}
          {formatBytes(item.file_size_bytes)}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-1">
          <QualityBadge status={item.quality_status} />
          {item.is_exact_duplicate && (
            <span className="rounded-full border border-fuchsia-700/60 bg-fuchsia-950/60 px-2 py-0.5 text-[10px] text-fuchsia-400">
              exact dup
            </span>
          )}
          {item.is_suspicious_duplicate && (
            <span className="rounded-full border border-violet-700/60 bg-violet-950/60 px-2 py-0.5 text-[10px] text-violet-400">
              near dup
            </span>
          )}
        </div>
        {item.flags.length > 0 && (
          <p className="mt-1 truncate text-[10px] text-slate-500" title={item.flags.join(", ")}>
            {item.flags.join(", ")}
          </p>
        )}
      </div>
    </div>
  );
}
