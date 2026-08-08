import { ChatWorkspace } from "@/components/chat-workspace";
import { PageHeading } from "@/components/page-heading";

export default function ChatPage() {
  return <div className="mx-auto max-w-[1500px] px-4 py-8 sm:px-8 sm:py-12"><PageHeading eyebrow="Core workspace" title="Think, ask, and act from one place." description="Provider-neutral chat with project context, durable history, and an execution trace you can actually audit." /><ChatWorkspace /></div>;
}
