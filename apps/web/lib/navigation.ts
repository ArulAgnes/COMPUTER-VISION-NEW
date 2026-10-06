/**
 * Single source of truth for dashboard navigation and skeleton page metadata.
 * Stage labels indicate when each section gains real functionality.
 */

export type NavItem = {
  /** URL path, "" for the dashboard root. */
  slug: string;
  href: string;
  label: string;
  title: string;
  description: string;
  /** Pipeline stage that implements this section. */
  stage: string;
  group: string;
  /** Metric labels rendered as "Not available" until computed for real. */
  metrics: string[];
};

const section = (
  slug: string,
  label: string,
  title: string,
  description: string,
  stage: string,
  group: string,
  metrics: string[] = [],
): NavItem => ({ slug, href: `/${slug}`, label, title, description, stage, group, metrics });

export const NAV_ITEMS: NavItem[] = [
  {
    slug: "",
    href: "/",
    label: "Dashboard",
    title: "Dashboard",
    description: "Live platform status. Values that have not been produced yet show as Not available.",
    stage: "Stage 1",
    group: "Overview",
    metrics: [],
  },
  section("dataset", "Dataset", "Dataset", "Dataset discovery: scan the read-only raw image folders and build a manifest.", "Stage 2", "Data Pipeline"),
  section("quality", "Quality", "Image Quality", "Measured quality checks: blur, brightness, duplicates, corrupted files.", "Stage 2", "Data Pipeline"),
  section("annotation", "Annotation", "Annotation", "Draw, edit, save and validate bounding-box annotations.", "Stage 3", "Data Pipeline"),
  section("split", "Split", "Dataset Split", "Deterministic train / validation / test split of original images.", "Stage 4", "Data Pipeline"),
  section("augmentation", "Augmentation", "Train-Only Augmentation", "Real geometric and photometric augmentation of training images only.", "Stage 5", "Data Pipeline"),
  section("dataset-versions", "Dataset Versions", "Dataset Versions", "Immutable dataset versions with lineage and statistics.", "Stage 5", "Data Pipeline"),
  section("training", "Training", "Training", "From-scratch training runs with live logs. No pretrained weights.", "Stage 7", "Models"),
  section("models", "Models", "Model Registry", "Registered checkpoints with metadata and status.", "Stage 7", "Models"),
  section("evaluation", "Evaluation", "Evaluation", "Real test-set metrics: IoU, precision, recall, F1, AP, mAP, confusion matrix.", "Stage 8", "Models"),
  section("error-analysis", "Error Analysis", "Error Analysis", "Categorized prediction errors: FP, FN, wrong class, poor localization.", "Stage 9", "Analysis"),
  section("data-diagnosis", "Data Diagnosis", "Data Diagnosis", "Derives likely data problems from measured evaluation errors.", "Stage 9", "Analysis"),
  section("recommendations", "Recommendations", "Recommendations", "Actionable data-collection recommendations with priority.", "Stage 9", "Analysis"),
  section("inference", "Inference", "Image Inference", "Upload an image and run the trained detector.", "Stage 10", "Inference"),
  section("camera", "Camera", "Camera Inference", "Capture frames from the browser camera and run detection.", "Stage 10", "Inference"),
  section("reports", "Reports", "Reports", "Generated reports from real project data.", "Planned", "Project"),
  section("settings", "Settings", "Settings", "Configuration loaded from configs/project.yaml.", "Stage 1", "Project"),
];

export const NAV_GROUPS: string[] = Array.from(new Set(NAV_ITEMS.map((item) => item.group)));

export function findSection(slug: string): NavItem | undefined {
  return NAV_ITEMS.find((item) => item.slug === slug && item.slug !== "");
}
