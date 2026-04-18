import type { Metadata } from "next";
import { Inter, Source_Serif_4, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import "driver.js/dist/driver.css";
import { Suspense } from "react";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { QueryProvider } from "@/components/providers/query-provider";
import { AuthProvider } from "@/components/providers/auth-provider";
import { JudgeModeProvider } from "@/components/demo/judge-mode-provider";
import { Toaster } from "@/components/ui/sonner";

const inter = Inter({
  subsets: ["latin", "vietnamese"],
  variable: "--font-inter",
  display: "swap",
});

const sourceSerif = Source_Serif_4({
  subsets: ["latin", "vietnamese"],
  variable: "--font-source-serif",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://govflow.vn";

export const metadata: Metadata = {
  title: {
    default: "GovFlow — Hệ thống xử lý thủ tục hành chính thông minh",
    template: "%s | GovFlow",
  },
  description:
    "GovFlow — Hệ thống xử lý thủ tục hành chính công thông minh, ứng dụng AI Qwen3 và đồ thị tri thức để tăng tốc xử lý hồ sơ hành chính tại Việt Nam.",
  metadataBase: new URL(siteUrl),
  icons: { icon: "/favicon.svg" },
  openGraph: {
    title: "GovFlow — Agentic TTHC Processing",
    description:
      "Ứng dụng AI Qwen3 và GraphRAG xử lý thủ tục hành chính công thông minh tại Việt Nam.",
    type: "website",
    locale: "vi_VN",
    url: siteUrl,
    siteName: "GovFlow",
  },
  twitter: {
    card: "summary_large_image",
    title: "GovFlow — Hệ thống TTHC thông minh",
    description:
      "Ứng dụng AI Qwen3 và GraphRAG xử lý thủ tục hành chính công thông minh tại Việt Nam.",
  },
  alternates: {
    canonical: siteUrl,
    languages: { "vi-VN": siteUrl },
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="vi"
      suppressHydrationWarning
      className={`${inter.variable} ${sourceSerif.variable} ${jetbrainsMono.variable}`}
    >
      <body className="antialiased">
        <ThemeProvider defaultTheme="light" storageKey="govflow-theme">
          <QueryProvider>
            <AuthProvider>
              <Suspense fallback={null}>
                <JudgeModeProvider>{children}</JudgeModeProvider>
              </Suspense>
              <Toaster />
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
