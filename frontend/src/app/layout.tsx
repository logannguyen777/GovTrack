import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GovFlow",
  description: "Agentic GraphRAG for Vietnamese TTHC",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
