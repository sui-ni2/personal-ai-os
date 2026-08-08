import { MemoryManager } from "@/components/memory-manager";
import { PageHeading } from "@/components/page-heading";

export default function MemoryPage() {
  return (
    <div className="page-frame">
      <PageHeading title="Memory" description="The preferences, rules, projects, and facts your AI can carry forward." />
      <MemoryManager />
    </div>
  );
}
