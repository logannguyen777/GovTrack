"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// StreamingText
// ---------------------------------------------------------------------------

interface StreamingTextProps {
  text: string;
  isStreaming: boolean;
  showCaret?: boolean;
  className?: string;
  ariaLive?: "polite" | "assertive";
}

/**
 * Renders streaming text with an optional blinking caret.
 *
 * When `isStreaming` is true and `showCaret` is not explicitly false, the last
 * character is wrapped in a span with the `.streaming-caret` class (defined in
 * globals.css) which appends an animated block cursor.
 */
export function StreamingText({
  text,
  isStreaming,
  showCaret = true,
  className,
  ariaLive = "polite",
}: StreamingTextProps) {
  const showActiveCaret = isStreaming && showCaret !== false;

  return (
    <span
      className={cn("whitespace-pre-wrap break-words", className)}
      aria-live={ariaLive}
      aria-atomic={false}
    >
      {showActiveCaret ? (
        <>
          {text.length > 1 ? text.slice(0, -1) : ""}
          <span className="streaming-caret">
            {text.length > 0 ? text[text.length - 1] : ""}
          </span>
        </>
      ) : (
        text
      )}
    </span>
  );
}
