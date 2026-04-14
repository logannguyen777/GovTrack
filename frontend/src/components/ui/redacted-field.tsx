"use client"

import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"

interface RedactedFieldProps {
  value: string
  isRevealed: boolean
  className?: string
}

// 400ms ease-out-quart matches the emphasis transition from @/lib/motion
const EMPHASIS_EASE = [0.25, 1, 0.5, 1] as const

export function RedactedField({ value, isRevealed, className }: RedactedFieldProps) {
  return (
    <span className={cn("relative inline-block", className)}>
      <AnimatePresence mode="wait" initial={false}>
        {isRevealed ? (
          <motion.span
            key="revealed"
            initial={{ filter: "blur(8px)", opacity: 0.6 }}
            animate={{ filter: "blur(0px)", opacity: 1 }}
            exit={{ filter: "blur(8px)", opacity: 0.6 }}
            transition={{ duration: 0.4, ease: EMPHASIS_EASE }}
            aria-hidden={false}
          >
            {value}
          </motion.span>
        ) : (
          <motion.span
            key="masked"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4, ease: EMPHASIS_EASE }}
            aria-label="Thông tin bị che giấu"
            className={cn(
              "inline-flex items-center px-2 py-0.5 rounded-sm",
              "font-mono text-[11px] tracking-widest font-medium select-none",
            )}
            style={{
              backgroundColor: "var(--text-primary)",
              color: "var(--bg-surface)",
            }}
          >
            [REDACTED]
          </motion.span>
        )}
      </AnimatePresence>
      {/* Screen-reader text always present */}
      <span className="sr-only">{isRevealed ? value : "Thông tin bị che giấu"}</span>
    </span>
  )
}
