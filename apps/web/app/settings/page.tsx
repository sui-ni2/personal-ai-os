import { PageHeading } from "@/components/page-heading";
import { SettingsPanel } from "@/components/settings-panel";

export default function SettingsPage() {
  return (
    <div className="page-frame">
      <PageHeading title="Settings" description="Manage your AI service, privacy, appearance, and advanced controls." />
      <SettingsPanel />
    </div>
  );
}
