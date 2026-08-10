const staticExport = process.env.PERSONAL_AI_OS_STATIC_EXPORT === "true";

/** @type {import('next').NextConfig} */
const nextConfig = {
  ...(staticExport ? { output: "export", trailingSlash: true, images: { unoptimized: true } } : {}),
  ...(!staticExport ? {
    async rewrites() {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
    },
  } : {}),
};

export default nextConfig;
