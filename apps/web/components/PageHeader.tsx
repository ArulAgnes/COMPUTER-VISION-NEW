type PageHeaderProps = {
  title: string;
  description: string;
  /** Pipeline stage that implements this section, e.g. "Stage 3". */
  stage?: string;
};

/** Consistent heading block for every section page. */
export default function PageHeader({ title, description, stage }: PageHeaderProps) {
  return (
    <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold text-white">{title}</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-400">{description}</p>
      </div>
      {stage && (
        <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs text-slate-400">
          {stage}
        </span>
      )}
    </header>
  );
}
