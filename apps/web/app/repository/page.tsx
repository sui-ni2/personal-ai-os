import { PageHeading } from "@/components/page-heading";
import { RepositoryManager } from "@/components/repository-manager";

export default function RepositoryPage() {
  return <div className="mx-auto max-w-6xl px-4 py-8 sm:px-8 sm:py-12"><PageHeading eyebrow="Audit layer" title="Context that outlives the chat." description="Artifact metadata and a durable event timeline keep decisions and execution evidence queryable." /><RepositoryManager /></div>;
}
