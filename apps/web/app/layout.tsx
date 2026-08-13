import type { Metadata, Viewport } from "next";
import { AppShell } from "@/components/app-shell";
import { AccessGate } from "@/components/access-gate";
import { PwaRegister } from "@/components/pwa-register";
import "./globals.css";

export const metadata: Metadata = {
  title: "Personal AI OS",
  description: "A user-controlled AI workspace for lasting projects and reusable outcomes",
  applicationName: "Personal AI OS",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/icons/app-icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/app-icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/app-icon-180.png", sizes: "180x180", type: "image/png" }],
  },
  appleWebApp: {
    capable: true,
    title: "Personal AI OS",
    statusBarStyle: "default",
  },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#f1e9dd" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <PwaRegister />
        <AccessGate><AppShell>{children}</AppShell></AccessGate>
      </body>
    </html>
  );
}
