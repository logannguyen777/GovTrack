import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const base =
    process.env.NEXT_PUBLIC_SITE_URL || "https://govflow.vn";

  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/portal", "/track", "/submit", "/assistant"],
        disallow: ["/auth", "/(internal)", "/api"],
      },
    ],
    sitemap: `${base}/sitemap.xml`,
  };
}
