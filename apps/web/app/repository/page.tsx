import { PageHeading } from "@/components/page-heading";
import { RepositoryManager } from "@/components/repository-manager";

export default function RepositoryPage() {
  return (
    <div className="page-frame">
      <PageHeading title="Repository" description="A timeline of what your AI has changed, saved, and connected." />
      <RepositoryManager />
    </div>
  );
}
