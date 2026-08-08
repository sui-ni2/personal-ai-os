import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Personal AI OS",
    short_name: "AI OS",
    description: "A provider-neutral personal AI workbench",
    start_url: "/chat",
    display: "standalone",
    background_color: "#f5f1e8",
    theme_color: "#f5f1e8"
  };
}
