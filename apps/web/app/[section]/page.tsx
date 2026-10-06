import { notFound } from "next/navigation";
import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import StatCard from "@/components/StatCard";
import { findSection } from "@/lib/navigation";

/** Skeleton page shared by all sections that do not have a dedicated page yet. */
export default async function SectionPage({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section: slug } = await params;
  const section = findSection(slug);

  if (!section) {
    notFound();
  }

  return (
    <div>
      <PageHeader
        title={section.title}
        description={section.description}
        stage={section.stage}
      />

      <EmptyState
        title={`${section.title} has not produced data yet`}
        message={`This section is implemented in ${section.stage}. Until then every value below remains Not available — nothing here is simulated.`}
      />

      {section.metrics.length > 0 && (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {section.metrics.map((metric) => (
            <StatCard key={metric} label={metric} value={null} />
          ))}
        </div>
      )}
    </div>
  );
}
