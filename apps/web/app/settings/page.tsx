import { PageHeading } from "@/components/page-heading";
import { SettingsPanel } from "@/components/settings-panel";

export default function SettingsPage() {
  return <div className="mx-auto max-w-6xl px-4 py-8 sm:px-8 sm:py-12"><PageHeading eyebrow="Configuration" title="Control connections without exposing secrets." description="The browser can choose providers and models. API key values remain server-side environment data." /><SettingsPanel /></div>;
}
