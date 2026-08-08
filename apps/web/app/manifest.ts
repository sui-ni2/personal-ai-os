import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Personal AI OS",
    short_name: "AI OS",
    description: "A provider-neutral personal AI workbench",
    start_url: "/",
    display: "standalone",
    background_color: "#f1e9dd",
    theme_color: "#f1e9dd"
  };
}
