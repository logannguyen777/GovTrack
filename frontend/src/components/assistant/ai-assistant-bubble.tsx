"use client";

import * as React from "react";
import { useRouter, usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import FocusTrap from "focus-trap-react";
import {
  Sparkles,
  X,
  Maximize2,
  Send,
  Paperclip,
  Square,
  Mic,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ChatMessageBubble } from "./chat-message-bubble";
import { QuickIntentChip } from "./quick-intent-chip";
import { DocumentAIExtractor } from "./document-ai-extractor";
import { useAIChat } from "@/hooks/use-ai-chat";
import { useDocumentExtract } from "@/hooks/use-document-extract";
import { useSubmitFormStore } from "@/lib/stores/submit-form-store";
import type { ChatMessageExtended } from "@/hooks/use-ai-chat";
import type { ExtractResponse } from "@/hooks/use-document-extract";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function useIsMobile() {
  const [mobile, setMobile] = React.useState(false);
  React.useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return mobile;
}

function deriveContext(pathname: string) {
  const caseMatch = pathname.match(/\/track\/([^/]+)/);
  if (caseMatch) return { type: "case" as const, ref: caseMatch[1] };

  const submitMatch = pathname.match(/\/submit\/([^/]+)/);
  if (submitMatch) return { type: "submit" as const, ref: submitMatch[1] };

  // Internal staff routes — map to existing context types so backend schema
  // stays stable; chip labels will surface staff-specific intents.
  const caseIdMatch = pathname.match(/\/(compliance|trace)\/([^/]+)/);
  if (caseIdMatch) return { type: "case" as const, ref: caseIdMatch[2] };

  return { type: "portal" as const };
}

// ---------------------------------------------------------------------------
// Typing indicator
// ---------------------------------------------------------------------------

function TypingIndicator() {
  return (
    <div className="my-2 flex items-center gap-2 px-4">
      <div
        className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full"
        style={{ background: "var(--gradient-qwen)" }}
        aria-hidden="true"
      >
        <Sparkles size={12} className="text-white" />
      </div>
      <div className="flex items-center gap-1 rounded-2xl rounded-bl-sm px-3 py-2"
        style={{
          background: "var(--gradient-qwen-soft)",
          border: "1px solid oklch(0.65 0.15 280 / 0.25)",
        }}
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="block h-1.5 w-1.5 rounded-full bg-purple-500 animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Suggestion card
// ---------------------------------------------------------------------------

function SuggestionCard({
  tthc_code,
  name,
  reason,
  confidence,
  onSubmit,
  onDetail,
}: {
  tthc_code: string;
  name: string;
  reason: string;
  confidence?: number;
  onSubmit: () => void;
  onDetail: () => void;
}) {
  return (
    <div
      className="mx-4 my-2 rounded-xl border p-3"
      style={{
        background: "var(--gradient-qwen-soft)",
        borderColor: "oklch(0.65 0.15 280 / 0.25)",
      }}
    >
      <div className="flex items-start gap-2">
        <Sparkles size={14} className="mt-0.5 shrink-0 text-purple-600" />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-[var(--text-primary)]">
            AI gợi ý:{" "}
            <span className="text-purple-700">{name}</span>
            {confidence !== undefined && (
              <span className="ml-1 text-[10px] text-[var(--text-muted)]">
                ({Math.round(confidence * 100)}%)
              </span>
            )}
          </p>
          <p className="mt-0.5 text-xs text-[var(--text-secondary)] line-clamp-2">
            {reason}
          </p>
        </div>
      </div>
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          onClick={onSubmit}
          className="flex-1 rounded-lg py-1.5 text-xs font-semibold text-white"
          style={{ background: "var(--gradient-qwen)" }}
        >
          Nộp ngay
        </button>
        <button
          type="button"
          onClick={onDetail}
          className="rounded-lg border border-[var(--border-default)] px-3 py-1.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] transition-colors"
        >
          Xem chi tiết
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Welcome state
// ---------------------------------------------------------------------------

function WelcomeState({
  onChipClick,
  contextType,
}: {
  onChipClick: (text: string) => void;
  contextType: "case" | "submit" | "portal";
}) {
  const chips =
    contextType === "case"
      ? [
          { label: "Hồ sơ đang ở bước nào?", text: "Hồ sơ của tôi đang ở bước nào?" },
          { label: "Cần bổ sung gì?", text: "Tôi cần bổ sung giấy tờ gì?" },
          { label: "Khi nào có kết quả?", text: "Khi nào hồ sơ của tôi có kết quả?" },
          { label: "Liên hệ cơ quan nào?", text: "Tôi cần liên hệ cơ quan nào?" },
        ]
      : contextType === "submit"
        ? [
            { label: "Hướng dẫn điền form", text: "Hướng dẫn tôi điền form này" },
            { label: "Giấy tờ cần chuẩn bị", text: "Tôi cần chuẩn bị những giấy tờ gì?" },
            { label: "Kiểm tra hồ sơ", text: "AI có thể kiểm tra hồ sơ của tôi không?" },
            { label: "Lệ phí nộp", text: "Lệ phí nộp hồ sơ này là bao nhiêu?" },
          ]
        : [
            { label: "Cấp phép xây dựng", text: "Tôi muốn xin cấp phép xây dựng" },
            { label: "Tra cứu hồ sơ", text: "Tra cứu hồ sơ của tôi" },
            { label: "Giấy tờ cần những gì?", text: "Giấy tờ cần những gì để nộp hồ sơ?" },
            { label: "Hướng dẫn bước nộp", text: "Hướng dẫn các bước nộp hồ sơ trực tuyến" },
          ];

  return (
    <div className="flex flex-col items-center justify-center px-6 py-8 text-center">
      <div
        className="flex h-12 w-12 items-center justify-center rounded-full"
        style={{ background: "var(--gradient-qwen)" }}
      >
        <Sparkles size={22} className="text-white" />
      </div>
      <h3 className="mt-3 font-semibold text-[var(--text-primary)]">
        Xin chào! Tôi là trợ lý AI
      </h3>
      <p className="mt-1 text-sm text-[var(--text-secondary)]">
        Cổng Dịch vụ công Thông minh. Anh/chị cần làm thủ tục gì?
      </p>
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {chips.map((c) => (
          <QuickIntentChip
            key={c.label}
            label={c.label}
            onClick={() => onChipClick(c.text)}
          />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Message list item (handles suggestions + extractor cards)
// ---------------------------------------------------------------------------

interface ExtractorCard {
  msgId: string;
  file: File;
  result?: ExtractResponse;
  isExtracting: boolean;
  error?: string;
}

function MessageItem({
  msg,
  extractorCard,
  onSuggestionSubmit,
  onSuggestionDetail,
}: {
  msg: ChatMessageExtended;
  extractorCard?: ExtractorCard;
  onSuggestionSubmit: (code: string, extractionId?: string) => void;
  onSuggestionDetail: (code: string) => void;
}) {
  const [thinkingOpen, setThinkingOpen] = React.useState(false);

  return (
    <>
      {/* Extractor card (user message attachment) */}
      {extractorCard && (
        <div className="px-4 my-2">
          <DocumentAIExtractor
            file={extractorCard.file}
            extractResult={extractorCard.result ?? null}
            isExtracting={extractorCard.isExtracting}
            extractError={extractorCard.error}
            onExtracted={() => {}}
            onReject={() => {}}
          />
        </div>
      )}

      {/* Message bubble */}
      <ChatMessageBubble
        role={msg.role}
        content={msg.content}
        timestamp={msg.createdAt}
        isStreaming={msg.isStreaming}
        citations={msg.citations}
        attachments={msg.attachments}
      />

      {/* Thinking section (collapsed) */}
      {msg.thinkingText && (
        <div className="mx-4 mb-1">
          <button
            type="button"
            onClick={() => setThinkingOpen((p) => !p)}
            className="flex items-center gap-1 text-[10px] text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
          >
            <ChevronDown
              size={10}
              className={cn("transition-transform", thinkingOpen ? "rotate-180" : "")}
            />
            Xem suy luận AI
          </button>
          {thinkingOpen && (
            <div
              className="mt-1 rounded-lg border border-[var(--border-subtle)] p-2 text-[10px] font-mono leading-relaxed whitespace-pre-wrap"
              style={{ color: "var(--text-muted)", backgroundColor: "var(--bg-subtle)" }}
            >
              {msg.thinkingText}
            </div>
          )}
        </div>
      )}

      {/* Tool calls */}
      {msg.toolCalls && msg.toolCalls.length > 0 && (
        <div className="mx-4 mb-1 flex flex-col gap-1">
          {msg.toolCalls.map((tc) => (
            <div
              key={tc.id}
              className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px]"
              style={{
                borderColor: "var(--border-subtle)",
                backgroundColor: "var(--bg-subtle)",
                color: "var(--text-muted)",
              }}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full shrink-0",
                  tc.status === "success"
                    ? "bg-[var(--accent-success)]"
                    : tc.status === "error"
                      ? "bg-[var(--accent-destructive)]"
                      : "bg-[var(--accent-warning)] animate-pulse",
                )}
              />
              {tc.name}
              {tc.status === "success" && " — xong"}
              {tc.status === "error" && " — lỗi"}
              {tc.status === "pending" && " — đang chạy"}
            </div>
          ))}
        </div>
      )}

      {/* Suggestions */}
      {msg.suggestions && msg.suggestions.length > 0 && !msg.isStreaming && (
        <div>
          {msg.suggestions.map((s) => (
            <SuggestionCard
              key={s.tthc_code}
              {...s}
              onSubmit={() => onSuggestionSubmit(s.tthc_code)}
              onDetail={() => onSuggestionDetail(s.tthc_code)}
            />
          ))}
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Composer
// ---------------------------------------------------------------------------

interface ComposerProps {
  isStreaming: boolean;
  onSend: (text: string) => void;
  onAbort: () => void;
  onFileAttach: (file: File) => void;
}

function Composer({ isStreaming, onSend, onAbort, onFileAttach }: ComposerProps) {
  const [text, setText] = React.useState("");
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  // Check Web Speech API support — start false (SSR-safe), update after mount
  const [speechSupported, setSpeechSupported] = React.useState(false);
  React.useEffect(() => {
    setSpeechSupported(
      typeof window !== "undefined" &&
        ("SpeechRecognition" in window || "webkitSpeechRecognition" in window),
    );
  }, []);
  const [isListening, setIsListening] = React.useState(false);
  const [interimTranscript, setInterimTranscript] = React.useState("");
  const recognitionRef = React.useRef<SpeechRecognition | null>(null);

  // Auto-resize textarea
  React.useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 96)}px`; // max 4 rows ≈ 96px
  }, [text]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setText("");
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      onFileAttach(file);
      e.target.value = "";
    }
  }

  function toggleVoice() {
    if (!speechSupported) return;

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      setInterimTranscript("");
      return;
    }

    const SRConstructor =
      window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!SRConstructor) return;

    const rec = new SRConstructor();
    rec.lang = "vi-VN";
    rec.continuous = false;
    rec.interimResults = true;

    rec.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += t;
        } else {
          interim += t;
        }
      }
      setInterimTranscript(interim);
      if (final) {
        setText((prev) => prev + final);
        setInterimTranscript("");
      }
    };

    rec.onend = () => {
      setIsListening(false);
      setInterimTranscript("");
    };
    rec.onerror = () => {
      setIsListening(false);
      setInterimTranscript("");
    };

    recognitionRef.current = rec;
    rec.start();
    setIsListening(true);
  }

  return (
    <div
      className="border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3"
      role="group"
      aria-label="Soạn tin nhắn"
    >
      <div className="flex items-end gap-2">
        {/* Attach */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          aria-label="Đính kèm tài liệu"
          className="shrink-0 rounded-lg p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] transition-colors"
        >
          <Paperclip size={16} />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf"
          onChange={handleFileChange}
          className="sr-only"
          aria-hidden="true"
        />

        {/* Textarea */}
        <div className="flex-1 flex flex-col min-w-0">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={
              isListening
                ? interimTranscript
                  ? interimTranscript
                  : "Đang nghe..."
                : "Nhập câu hỏi..."
            }
            disabled={isStreaming}
            aria-label="Tin nhắn"
            aria-live={isListening ? "polite" : undefined}
            className={cn(
              "w-full resize-none rounded-xl border bg-[var(--bg-app)] px-3 py-2 text-sm outline-none",
              "placeholder:text-[var(--text-muted)] leading-normal",
              "focus:border-purple-400 focus:ring-1 focus:ring-purple-300",
              isListening
                ? "border-red-400 ring-1 ring-red-300 placeholder:text-red-400"
                : "border-[var(--border-default)]",
              "disabled:opacity-50",
              "max-h-24 overflow-y-auto",
            )}
          />
          {isListening && interimTranscript && (
            <p
              className="mt-0.5 px-1 text-[10px] leading-tight truncate"
              style={{ color: "var(--text-muted)" }}
              aria-live="polite"
            >
              {interimTranscript}
            </p>
          )}
        </div>

        {/* Voice (if supported) */}
        {speechSupported && !isStreaming && (
          <button
            type="button"
            onClick={toggleVoice}
            aria-label={isListening ? "Dừng ghi âm" : "Ghi âm giọng nói"}
            aria-pressed={isListening}
            className={cn(
              "relative shrink-0 rounded-lg p-1.5 transition-colors",
              isListening
                ? "bg-red-100 text-red-600"
                : "text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]",
            )}
          >
            {isListening && (
              <span
                className="absolute inset-0 rounded-lg animate-ping bg-red-300 opacity-50"
                aria-hidden="true"
              />
            )}
            <Mic size={16} className="relative" />
          </button>
        )}

        {/* Abort / Send */}
        {isStreaming ? (
          <button
            type="button"
            onClick={onAbort}
            aria-label="Dừng phản hồi"
            className="shrink-0 rounded-lg p-1.5 text-[var(--accent-destructive)] hover:bg-[var(--accent-destructive)]/10 transition-colors"
          >
            <Square size={16} />
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={!text.trim()}
            aria-label="Gửi tin nhắn"
            className="shrink-0 rounded-xl p-1.5 text-white transition-opacity hover:opacity-90 disabled:opacity-40"
            style={{ background: "var(--gradient-qwen)" }}
          >
            <Send size={16} />
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Panel content (shared between desktop overlay + mobile Sheet)
// ---------------------------------------------------------------------------

interface PanelContentProps {
  onClose: () => void;
  onExpand?: () => void;
  contextType: "case" | "submit" | "portal";
}

function PanelContent({ onClose, onExpand, contextType }: PanelContentProps) {
  const router = useRouter();
  const context = contextType === "case"
    ? { type: "case" as const }
    : contextType === "submit"
      ? { type: "submit" as const }
      : { type: "portal" as const };

  const { messages, isStreaming, send, abort, error } = useAIChat({ context });
  const extractMutation = useDocumentExtract();
  const setFromExtraction = useSubmitFormStore((s) => s.setFromExtraction);

  // Extractor cards keyed by message id
  const [extractorCards, setExtractorCards] = React.useState<
    Record<string, ExtractorCard>
  >({});

  const listRef = React.useRef<HTMLDivElement>(null);
  const [userScrolled, setUserScrolled] = React.useState(false);

  // Auto-scroll
  React.useEffect(() => {
    if (!userScrolled && listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, userScrolled]);

  function handleScroll() {
    const el = listRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setUserScrolled(!atBottom);
  }

  function scrollToBottom() {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
      setUserScrolled(false);
    }
  }

  async function handleFileAttach(file: File) {
    // Append a placeholder user message
    const msgId = crypto.randomUUID();
    setExtractorCards((prev) => ({
      ...prev,
      [msgId]: { msgId, file, isExtracting: true },
    }));

    await send(`[Đính kèm: ${file.name}]`, [
      { name: file.name, data: "", type: file.type.startsWith("image/") ? "image" : "pdf" },
    ]);

    try {
      const result = await extractMutation.mutateAsync({ file });
      setExtractorCards((prev) => ({
        ...prev,
        [msgId]: { ...prev[msgId], isExtracting: false, result },
      }));
    } catch (err) {
      setExtractorCards((prev) => ({
        ...prev,
        [msgId]: {
          ...prev[msgId],
          isExtracting: false,
          error: (err as Error).message || "Lỗi trích xuất",
        },
      }));
    }
  }

  function handleExtracted(result: ExtractResponse) {
    // Fill form store if in submit context
    if (contextType === "submit") {
      setFromExtraction(result.entities);
    }
  }

  function handleSuggestionSubmit(code: string) {
    router.push(`/submit/${code}`);
    onClose();
  }

  function handleSuggestionDetail(code: string) {
    router.push(`/portal?tthc=${code}`);
    onClose();
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div
        className="flex h-14 shrink-0 items-center gap-3 px-4"
        style={{ background: "var(--gradient-qwen)" }}
      >
        <Sparkles size={16} className="text-white/80 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white leading-tight truncate">
            Trợ lý AI — Cổng DVC
          </p>
        </div>
        <div className="flex items-center gap-1">
          {onExpand && (
            <button
              type="button"
              onClick={onExpand}
              aria-label="Mở rộng"
              className="rounded-lg p-1.5 text-white/70 hover:text-white hover:bg-white/10 transition-colors"
            >
              <Maximize2 size={14} />
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng trợ lý AI"
            className="rounded-lg p-1.5 text-white/70 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div
          className="shrink-0 px-4 py-2 text-xs text-[var(--accent-destructive)] bg-[var(--accent-destructive)]/10 border-b border-[var(--border-subtle)]"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* Message list */}
      <div
        ref={listRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto py-2"
        role="log"
        aria-label="Lịch sử hội thoại"
        aria-live="polite"
      >
        {messages.length === 0 ? (
          <WelcomeState
            onChipClick={(t) => void send(t)}
            contextType={contextType}
          />
        ) : (
          messages.map((msg, i) => {
            // Match extractor card to the last user message before the card
            const card = Object.values(extractorCards).find(
              (c) => c.msgId === msg.id,
            );
            return (
              <MessageItem
                key={msg.id}
                msg={{
                  ...msg,
                  // For extractor messages, clear content so we don't show raw text
                  content: card ? "" : msg.content,
                }}
                extractorCard={card}
                onSuggestionSubmit={handleSuggestionSubmit}
                onSuggestionDetail={handleSuggestionDetail}
              />
            );
          })
        )}
        {isStreaming && messages[messages.length - 1]?.role === "user" && (
          <TypingIndicator />
        )}
      </div>

      {/* Scroll to bottom chip */}
      <AnimatePresence>
        {userScrolled && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="absolute bottom-16 right-4 z-10"
          >
            <button
              type="button"
              onClick={scrollToBottom}
              className="flex items-center gap-1 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs text-[var(--text-secondary)] shadow-md hover:bg-[var(--bg-subtle)] transition-colors"
            >
              <ChevronDown size={12} />
              Mới
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Composer */}
      <Composer
        isStreaming={isStreaming}
        onSend={(t) => void send(t)}
        onAbort={abort}
        onFileAttach={handleFileAttach}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main exported component
// ---------------------------------------------------------------------------

export function AIAssistantBubble() {
  const pathname = usePathname();
  const router = useRouter();
  const isMobile = useIsMobile();
  const [open, setOpen] = React.useState(false);
  const context = deriveContext(pathname ?? "");

  function handleExpand() {
    setOpen(false);
    router.push("/assistant");
  }

  // Keyboard: Escape to close
  React.useEffect(() => {
    if (!open) return;
    function handler(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  // ---- Mobile: Sheet ----
  if (isMobile) {
    return (
      <>
        {/* FAB */}
        <AnimatePresence>
          {!open && (
            <motion.button
              type="button"
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={() => setOpen(true)}
              aria-label="Mở trợ lý AI"
              className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full shadow-lg"
              style={{
                background: "var(--gradient-qwen)",
                boxShadow: "var(--shadow-qwen-glow)",
              }}
            >
              <Sparkles size={22} className="text-white" />
            </motion.button>
          )}
        </AnimatePresence>

        <Sheet open={open} onOpenChange={setOpen}>
          <SheetContent side="bottom" showCloseButton={false} className="h-[92dvh] p-0 flex flex-col">
            <SheetHeader className="sr-only">
              <SheetTitle>Trợ lý AI Cổng DVC</SheetTitle>
            </SheetHeader>
            <PanelContent
              onClose={() => setOpen(false)}
              onExpand={handleExpand}
              contextType={context.type}
            />
          </SheetContent>
        </Sheet>
      </>
    );
  }

  // ---- Desktop: fixed panel ----
  return (
    <>
      {/* FAB */}
      <AnimatePresence>
        {!open && (
          <motion.button
            type="button"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setOpen(true)}
            aria-label="Mở trợ lý AI"
            className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full shadow-lg"
            style={{
              background: "var(--gradient-qwen)",
              boxShadow: "var(--shadow-qwen-glow)",
            }}
          >
            {/* Pulse ring */}
            <span
              className="absolute h-full w-full rounded-full animate-ping opacity-25"
              style={{ background: "var(--gradient-qwen)", animationDuration: "8s" }}
            />
            <Sparkles size={22} className="text-white relative" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Panel */}
      <AnimatePresence>
        {open && (
          <FocusTrap
            focusTrapOptions={{
              initialFocus: false,
              fallbackFocus: "[data-bubble-panel]",
              allowOutsideClick: true,
            }}
          >
            <motion.div
              data-bubble-panel=""
              role="dialog"
              aria-label="Trợ lý AI"
              aria-modal="true"
              initial={{ scale: 0.8, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.8, opacity: 0, y: 20 }}
              transition={{ duration: 0.25, ease: [0.25, 1, 0.5, 1] }}
              style={{
                transformOrigin: "bottom right",
                borderRadius: "var(--radius-bubble)",
                height: "560px",
              }}
              className="fixed bottom-6 right-6 z-50 flex w-[400px] flex-col overflow-hidden border border-[var(--border-subtle)] bg-[var(--bg-surface)] shadow-xl"
              tabIndex={-1}
            >
              <PanelContent
                onClose={() => setOpen(false)}
                onExpand={handleExpand}
                contextType={context.type}
              />
            </motion.div>
          </FocusTrap>
        )}
      </AnimatePresence>
    </>
  );
}
