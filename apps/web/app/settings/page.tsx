import { PageHeading } from "@/components/page-heading";
import { SettingsPanel } from "@/components/settings-panel";

export default function SettingsPage() {
  return (
    <div className="page-frame">
      <PageHeading title="Settings" description="Manage models, tool connections, appearance, and local data without exposing secrets." />
      <SettingsPanel />
    </div>
  );
}
