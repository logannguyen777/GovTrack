"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { FileText, ExternalLink } from "lucide-react";

interface DocItem {
  id: string;
  name: string;
  type: string;
  status: string;
}

interface DocumentListProps {
  documents: DocItem[];
}

export function DocumentList({ documents }: DocumentListProps) {
  const router = useRouter();

  return (
    <div
      className="rounded-lg border p-4"
      style={{
        borderColor: "var(--border-subtle)",
        backgroundColor: "var(--bg-surface)",
      }}
    >
      <h3
        className="mb-3 text-sm font-semibold"
        style={{ color: "var(--text-primary)" }}
      >
        Tài liệu ({documents.length})
      </h3>

      {documents.length === 0 ? (
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Chưa có tài liệu
        </p>
      ) : (
        <div className="space-y-2">
          {documents.map((doc) => (
            <div
              key={doc.id}
              role="button"
              tabIndex={0}
              onClick={() => router.push(`/documents/${doc.id}`)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  router.push(`/documents/${doc.id}`);
                }
              }}
              className="flex cursor-pointer items-center justify-between rounded-md border p-2 text-sm transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]"
              style={{ borderColor: "var(--border-subtle)" }}
              aria-label={`Mở tài liệu ${doc.name}`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <FileText
                  className="h-4 w-4 shrink-0"
                  style={{ color: "var(--text-muted)" }}
                  aria-hidden="true"
                />
                <span className="truncate" style={{ color: "var(--text-primary)" }}>
                  {doc.name}
                </span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span
                  className="rounded px-1.5 py-0.5 text-[10px]"
                  style={{
                    backgroundColor: "var(--bg-subtle)",
                    color: "var(--text-muted)",
                  }}
                >
                  {doc.status}
                </span>
                <ExternalLink
                  className="h-3 w-3"
                  style={{ color: "var(--text-muted)" }}
                  aria-hidden="true"
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
