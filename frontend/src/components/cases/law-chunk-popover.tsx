"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import { SkeletonCard } from "@/components/ui/skeleton-card";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

// Shape returned by backend GET /search/law/chunk/{id}
interface LawChunkAPI {
  chunk_id: string;
  law_id: string;
  article_number: string;
  clause_path: string;
  chunk_index: number;
  title: string | null;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

interface LawChunk {
  chunk_id: string;
  law_name: string;
  article: string;
  content: string;
  clause_path?: string;
  law_id?: string;
  source_url?: string;
}

function mapChunk(raw: LawChunkAPI): LawChunk {
  return {
    chunk_id: raw.chunk_id,
    law_name: raw.title || raw.law_id,
    article: raw.article_number,
    content: raw.content,
    clause_path: raw.clause_path,
    law_id: raw.law_id,
  };
}

// ---------------------------------------------------------------------------
// LawChunkPopover
// ---------------------------------------------------------------------------

interface LawChunkPopoverProps {
  chunkId: string;
  trigger: React.ReactNode;
  /** Fallback metadata when the backend endpoint is unavailable */
  fallback?: {
    lawName?: string;
    article?: string;
  };
}

export function LawChunkPopover({
  chunkId,
  trigger,
  fallback,
}: LawChunkPopoverProps) {
  const { data, isLoading, isError } = useQuery<LawChunk>({
    queryKey: ["law-chunk", chunkId],
    queryFn: async () => {
      const r = await fetch(`/api/search/law/chunk/${encodeURIComponent(chunkId)}`);
      if (!r.ok) throw new Error(`${r.status}`);
      const raw = (await r.json()) as LawChunkAPI;
      return mapChunk(raw);
    },
    staleTime: Infinity,
    enabled: Boolean(chunkId),
    retry: false,
  });

  return (
    <Popover>
      <PopoverTrigger render={trigger as React.ReactElement<Record<string, unknown>>} />
      <PopoverContent
        className="w-[480px] max-h-[600px] overflow-auto p-4"
        side="top"
        align="start"
      >
        {isLoading && <SkeletonCard />}

        {isError && fallback && (
          <div>
            <h4
              className="font-semibold text-sm"
              style={{ color: "var(--text-primary)" }}
            >
              {fallback.article ?? "—"} · {fallback.lawName ?? "Văn bản pháp luật"}
            </h4>
            <p
              className="mt-2 text-xs"
              style={{ color: "var(--text-muted)" }}
            >
              Không thể tải nội dung chi tiết ({chunkId})
            </p>
          </div>
        )}

        {data && (
          <>
            <div>
              <p
                className="text-[10px] font-semibold uppercase tracking-wide mb-1"
                style={{ color: "var(--text-muted)" }}
              >
                Căn cứ pháp lý
              </p>
              <h4
                className="font-semibold text-sm leading-snug"
                style={{ color: "var(--text-primary)" }}
              >
                {data.law_name}
              </h4>
              <p
                className="text-xs mt-0.5"
                style={{ color: "var(--text-secondary)" }}
              >
                {data.article}
                {data.clause_path ? ` · ${data.clause_path}` : ""}
              </p>
            </div>

            <Separator className="my-3" />

            <pre
              className="text-xs whitespace-pre-wrap leading-relaxed break-words"
              style={{
                color: "var(--text-secondary)",
                fontFamily: "var(--font-serif, 'Source Serif 4', serif)",
              }}
            >
              {data.content}
            </pre>

            {data.source_url && (
              <>
                <Separator className="my-3" />
                <a
                  href={data.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs underline underline-offset-2 hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)] rounded-sm"
                  style={{ color: "var(--accent-primary)" }}
                >
                  Mở văn bản đầy đủ ↗
                </a>
              </>
            )}
          </>
        )}
      </PopoverContent>
    </Popover>
  );
}
