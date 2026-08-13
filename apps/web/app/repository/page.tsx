import { PageHeading } from "@/components/page-heading";
import { RepositoryManager } from "@/components/repository-manager";

export default function RepositoryPage() {
  return (
    <div className="page-frame">
      <PageHeading title="Outcomes" description="Keep useful results and review the activity that produced them." />
      <RepositoryManager />
    </div>
  );
}
