type StatCardProps = {
  label: string;
  /** null / undefined renders the honest "Not available" state. */
  value: string | number | null | undefined;
  hint?: string;
  /** Emphasize the card (e.g. headline metrics). */
  emphasis?: boolean;
};

/** Single statistic tile. Never invents a value. */
export default function StatCard({ label, value, hint, emphasis = false }: StatCardProps) {
  const missing = value === null || value === undefined || value === "";
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p
        className={[
          "mt-2 font-mono",
          emphasis ? "text-2xl" : "text-lg",
          missing ? "text-slate-600 italic" : "text-white",
        ].join(" ")}
      >
        {missing ? "Not available" : String(value)}
      </p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}
