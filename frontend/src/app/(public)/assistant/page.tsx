"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  Send,
  Square,
  Paperclip,
  Mic,
  ChevronDown,
  ArrowLeft,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useAIChat } from "@/hooks/use-ai-chat";
import { ChatMessageBubble } from "@/components/assistant/chat-message-bubble";
import { QuickIntentChip } from "@/components/assistant/quick-intent-chip";
import type { ChatMessageExtended } from "@/hooks/use-ai-chat";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PORTAL_CHIPS = [
  { label: "Cấp phép xây dựng", text: "Tôi muốn xin cấp phép xây dựng nhà ở" },
  {
    label: "Đăng ký kinh doanh",
    text: "Tôi cần đăng ký giấy phép kinh doanh hộ cá thể",
  },
  { label: "Lý lịch tư pháp", text: "Thủ tục xin cấp phiếu lý lịch tư pháp" },
  {
    label: "Đất đai & nhà ở",
    text: "Tôi cần sang tên sổ đỏ cho mảnh đất vừa mua",
  },
  {
    label: "Giấy tờ hộ tịch",
    text: "Thủ tục đăng ký khai sinh cho trẻ sơ sinh",
  },
  {
    label: "Tra cứu thủ tục",
    text: "Liệt kê các thủ tục hành chính phổ biến nhất",
  },
];

// ---------------------------------------------------------------------------
// TypingIndicator
// ---------------------------------------------------------------------------

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 px-2 py-1">
      <div
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
        style={{ background: "var(--gradient-qwen)" }}
        aria-hidden="true"
      >
        <Sparkles size={14} className="text-white" />
      </div>
      <div
        className="flex items-center gap-1 rounded-2xl rounded-bl-sm px-3 py-2"
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
// WelcomeBlock
// ---------------------------------------------------------------------------

function WelcomeBlock({ onPick }: { onPick: (text: string) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col items-center justify-center py-16 text-center px-4"
    >
      <div
        className="flex h-16 w-16 items-center justify-center rounded-2xl"
        style={{ background: "var(--gradient-qwen)" }}
        aria-hidden="true"
      >
        <Sparkles size={28} className="text-white" />
      </div>
      <h2 className="mt-5 text-xl font-semibold text-[var(--text-primary)]">
        Xin chào! Tôi là trợ lý AI Cổng DVC
      </h2>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-[var(--text-secondary)]">
        Hỏi bất cứ câu nào về thủ tục hành chính. Tôi sẽ trả lời với trích
        dẫn luật cụ thể, được hỗ trợ bởi Qwen3&#8209;Max.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-2 max-w-xl">
        {PORTAL_CHIPS.map((c) => (
          <QuickIntentChip
            key={c.label}
            label={c.label}
            onClick={() => onPick(c.text)}
          />
        ))}
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// ThinkingSection (collapsed)
// ---------------------------------------------------------------------------

function ThinkingSection({ text }: { text: string }) {
  const [open, setOpen] = React.useState(false);
  return (
    <div className="mb-1">
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className="flex items-center gap-1 text-[10px] text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
      >
        <ChevronDown
          size={10}
          className={cn("transition-transform", open ? "rotate-180" : "")}
        />
        Xem suy luận AI
      </button>
      {open && (
        <div
          className="mt-1 rounded-lg border border-[var(--border-subtle)] p-2 text-[10px] font-mono leading-relaxed whitespace-pre-wrap"
          style={{ color: "var(--text-muted)", backgroundColor: "var(--bg-subtle)" }}
        >
          {text}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// MessageRow
// ---------------------------------------------------------------------------

function MessageRow({ msg }: { msg: ChatMessageExtended }) {
  return (
    <div className="space-y-1">
      <ChatMessageBubble
        role={msg.role}
        content={msg.content}
        timestamp={msg.createdAt}
        isStreaming={msg.isStreaming}
        citations={msg.citations}
        attachments={msg.attachments}
      />
      {msg.thinkingText && <ThinkingSection text={msg.thinkingText} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Composer
// ---------------------------------------------------------------------------

interface ComposerProps {
  isStreaming: boolean;
  onSend: (text: string) => void;
  onAbort: () => void;
  onFileAttach?: (file: File) => void;
}

function Composer({ isStreaming, onSend, onAbort, onFileAttach }: ComposerProps) {
  const [text, setText] = React.useState("");
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  // Web Speech API — start as false (SSR-safe), then update after mount to avoid hydration mismatch
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

  // Auto-resize
  React.useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
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
      onFileAttach?.(file);
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
    rec.onend = () => { setIsListening(false); setInterimTranscript(""); };
    rec.onerror = () => { setIsListening(false); setInterimTranscript(""); };
    recognitionRef.current = rec;
    rec.start();
    setIsListening(true);
  }

  return (
    <div className="space-y-1">
      <div className="flex items-end gap-2">
        {/* Attach */}
        {onFileAttach && (
          <>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              aria-label="Đính kèm tài liệu"
              className="shrink-0 rounded-lg p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] transition-colors"
            >
              <Paperclip size={18} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,.pdf"
              onChange={handleFileChange}
              className="sr-only"
              aria-hidden="true"
            />
          </>
        )}

        {/* Textarea */}
        <div className="flex-1 min-w-0">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={
              isListening
                ? interimTranscript || "Đang nghe..."
                : "Nhập câu hỏi về thủ tục hành chính..."
            }
            disabled={isStreaming}
            aria-label="Câu hỏi"
            className={cn(
              "w-full resize-none rounded-xl border px-4 py-3 text-sm outline-none leading-normal",
              "placeholder:text-[var(--text-muted)]",
              "focus:border-purple-400 focus:ring-2 focus:ring-purple-300/40",
              isListening
                ? "border-red-400 ring-2 ring-red-200 placeholder:text-red-400"
                : "border-[var(--border-default)] bg-[var(--bg-surface)]",
              "disabled:opacity-50",
              "max-h-32 overflow-y-auto",
            )}
          />
          {isListening && interimTranscript && (
            <p
              className="mt-1 px-1 text-xs leading-tight text-[var(--text-muted)]"
              aria-live="polite"
            >
              {interimTranscript}
            </p>
          )}
        </div>

        {/* Voice */}
        {speechSupported && !isStreaming && (
          <button
            type="button"
            onClick={toggleVoice}
            aria-label={isListening ? "Dừng ghi âm" : "Ghi âm giọng nói"}
            aria-pressed={isListening}
            className={cn(
              "relative shrink-0 rounded-xl p-2.5 transition-colors",
              isListening
                ? "bg-red-100 text-red-600"
                : "text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]",
            )}
          >
            {isListening && (
              <span
                className="absolute inset-0 rounded-xl animate-ping bg-red-300 opacity-40"
                aria-hidden="true"
              />
            )}
            <Mic size={18} className="relative" />
          </button>
        )}

        {/* Abort / Send */}
        {isStreaming ? (
          <button
            type="button"
            onClick={onAbort}
            aria-label="Dừng phản hồi"
            className="shrink-0 rounded-xl p-2.5 text-[var(--accent-destructive)] hover:bg-[var(--accent-destructive)]/10 transition-colors"
          >
            <Square size={18} />
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={!text.trim()}
            aria-label="Gửi câu hỏi"
            className="shrink-0 rounded-xl p-2.5 text-white transition-opacity hover:opacity-90 disabled:opacity-40"
            style={{ background: "var(--gradient-qwen)" }}
          >
            <Send size={18} />
          </button>
        )}
      </div>
      <p className="text-center text-[10px] text-[var(--text-muted)]">
        Trả lời bởi Qwen3&#8209;Max · Tra cứu luật Việt Nam real-time
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AssistantPage
// ---------------------------------------------------------------------------

export default function AssistantPage() {
  const router = useRouter();
  const { messages, isStreaming, send, abort, error } = useAIChat({
    context: { type: "portal" },
  });

  const listRef = React.useRef<HTMLDivElement>(null);
  const [userScrolled, setUserScrolled] = React.useState(false);

  // Auto-scroll to bottom
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

  return (
    <div
      className="flex flex-col"
      style={{ height: "calc(100vh - 64px)" }}
    >
      <div className="mx-auto w-full max-w-3xl flex flex-col h-full px-4">
        {/* Header */}
        <header className="flex items-center gap-3 border-b border-[var(--border-subtle)] py-4 shrink-0">
          <button
            type="button"
            onClick={() => router.back()}
            aria-label="Quay lại"
            className="rounded-lg p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] transition-colors"
          >
            <ArrowLeft size={18} />
          </button>
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
            style={{ background: "var(--gradient-qwen)" }}
            aria-hidden="true"
          >
            <Sparkles size={18} className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-lg font-semibold text-[var(--text-primary)] leading-tight">
              Trợ lý AI Cổng DVC
            </h1>
            <p className="text-xs text-[var(--text-muted)] leading-tight mt-0.5">
              Hỏi về thủ tục hành chính — có trích dẫn luật cụ thể
            </p>
          </div>
        </header>

        {/* Error banner */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="shrink-0 overflow-hidden"
            >
              <div
                className="px-4 py-2 text-sm text-[var(--accent-destructive)] bg-[var(--accent-destructive)]/10 border-b border-[var(--border-subtle)]"
                role="alert"
              >
                {error}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Messages */}
        <main
          ref={listRef}
          onScroll={handleScroll}
          className="relative flex-1 overflow-y-auto py-6 space-y-4"
          role="log"
          aria-label="Lịch sử hội thoại"
          aria-live="polite"
        >
          {messages.length === 0 ? (
            <WelcomeBlock onPick={(t) => void send(t)} />
          ) : (
            messages.map((msg) => <MessageRow key={msg.id} msg={msg} />)
          )}
          {isStreaming && messages[messages.length - 1]?.role === "user" && (
            <TypingIndicator />
          )}

          {/* Scroll-to-bottom chip */}
          <AnimatePresence>
            {userScrolled && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 8 }}
                className="sticky bottom-2 flex justify-center"
              >
                <button
                  type="button"
                  onClick={scrollToBottom}
                  className="flex items-center gap-1 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs text-[var(--text-secondary)] shadow-md hover:bg-[var(--bg-subtle)] transition-colors"
                >
                  <ChevronDown size={12} />
                  Mới nhất
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        {/* Composer */}
        <footer className="shrink-0 border-t border-[var(--border-subtle)] py-4">
          <Composer
            isStreaming={isStreaming}
            onSend={(t) => void send(t)}
            onAbort={abort}
          />
        </footer>
      </div>
    </div>
  );
}
