import { MemoryManager } from "@/components/memory-manager";
import { PageHeading } from "@/components/page-heading";

export default function MemoryPage() {
  return <div className="mx-auto max-w-6xl px-4 py-8 sm:px-8 sm:py-12"><PageHeading eyebrow="Durable context" title="Memory with provenance." description="Store rules, preferences, and facts as explicit records. Every item has a source and lifecycle status." /><MemoryManager /></div>;
}
