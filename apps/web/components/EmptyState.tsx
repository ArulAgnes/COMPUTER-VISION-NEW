type EmptyStateProps = {
  title: string;
  message: string;
};

/** Truthful empty state used until a stage produces real data. */
export default function EmptyState({ title, message }: EmptyStateProps) {
  return (
    <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/40 p-8 text-center">
      <p className="text-sm font-medium text-slate-300">{title}</p>
      <p className="mx-auto mt-2 max-w-xl text-sm text-slate-500">{message}</p>
      <p className="mt-4 text-xs uppercase tracking-wider text-slate-600">Not available</p>
    </div>
  );
}
