import { PageHeading } from "@/components/page-heading";
import { ProjectsGrid } from "@/components/projects-grid";

export default function ProjectsPage() {
  return (
    <div className="page-frame">
      <PageHeading title="Projects" description="Separate spaces for different kinds of work, all built on the same personal AI core." />
      <ProjectsGrid />
    </div>
  );
}
