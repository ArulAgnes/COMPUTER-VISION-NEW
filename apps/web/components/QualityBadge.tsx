type QualityBadgeProps = {
  status: string | null | undefined;
};

const STYLES: Record<string, string> = {
  PASS: "border-emerald-700/60 bg-emerald-950/60 text-emerald-400",
  REVIEW: "border-amber-700/60 bg-amber-950/60 text-amber-400",
  FAIL: "border-red-700/60 bg-red-950/60 text-red-400",
};

/** Colored PASS / REVIEW / FAIL badge; unknown status renders honestly. */
export default function QualityBadge({ status }: QualityBadgeProps) {
  if (!status) {
    return (
      <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-500">
        Not available
      </span>
    );
  }
  const style = STYLES[status] ?? "border-slate-700 bg-slate-900 text-slate-400";
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide ${style}`}
    >
      {status}
    </span>
  );
}
