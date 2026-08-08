import { PageHeading } from "@/components/page-heading";
import { ProjectsGrid } from "@/components/projects-grid";

export default function ProjectsPage() {
  return <div className="mx-auto max-w-6xl px-4 py-8 sm:px-8 sm:py-12"><PageHeading eyebrow="Extension boundary" title="Projects plug in. The core stays general." description="General proves the system has no Soccer dependency. Soccer is an example module registered through the same contract." /><ProjectsGrid /></div>;
}
