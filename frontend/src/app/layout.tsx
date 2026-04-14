import type { Metadata } from "next";
import { Inter, Source_Serif_4, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { QueryProvider } from "@/components/providers/query-provider";
import { AuthProvider } from "@/components/providers/auth-provider";
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

export const metadata: Metadata = {
  title: {
    default: "GovFlow - Agentic TTHC Processing",
    template: "%s | GovFlow",
  },
  description:
    "Hệ thống xử lý thủ tục hành chính thông minh với AI - Powered by Qwen3",
  icons: { icon: "/favicon.svg" },
  openGraph: {
    title: "GovFlow - Agentic TTHC Processing",
    description:
      "Agentic GraphRAG for Vietnamese Public Administrative Services",
    type: "website",
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
        <ThemeProvider defaultTheme="dark" storageKey="govflow-theme">
          <QueryProvider>
            <AuthProvider>
              {children}
              <Toaster />
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
