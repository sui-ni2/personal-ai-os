import type { MetadataRoute } from "next";

export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Personal AI OS",
    short_name: "AI OS",
    description: "A provider-neutral personal AI workbench",
    id: "/",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait-primary",
    background_color: "#f1e9dd",
    theme_color: "#f1e9dd",
    categories: ["productivity", "utilities"],
    shortcuts: [
      {
        name: "New text conversation",
        short_name: "New chat",
        description: "Start a new text conversation",
        url: "/chat?new=1&mode=text",
        icons: [{ src: "/icons/app-icon-192.png", sizes: "192x192", type: "image/png" }],
      },
      {
        name: "Start GPT Live",
        short_name: "GPT Live",
        description: "Open a new realtime voice conversation",
        url: "/chat?new=1&mode=live",
        icons: [{ src: "/icons/app-icon-192.png", sizes: "192x192", type: "image/png" }],
      },
      {
        name: "Open Memory",
        short_name: "Memory",
        description: "Review saved long-term memory",
        url: "/memory",
        icons: [{ src: "/icons/app-icon-192.png", sizes: "192x192", type: "image/png" }],
      },
    ],
    icons: [
      { src: "/icons/app-icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/app-icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/app-icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
