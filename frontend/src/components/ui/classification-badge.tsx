import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const classificationVariants = cva(
  [
    "inline-flex items-center gap-1 rounded px-2 py-0.5",
    "text-[10px] font-semibold uppercase tracking-widest",
    "select-none whitespace-nowrap",
    "transition-opacity duration-150",
  ].join(" "),
  {
    variants: {
      level: {
        unclassified: [
          "text-white",
        ].join(" "),
        confidential: [
          "text-black",
        ].join(" "),
        secret: [
          "text-white",
        ].join(" "),
        "top-secret": [
          "text-white animate-pulse",
        ].join(" "),
      },
    },
    defaultVariants: {
      level: "unclassified",
    },
  }
)

const LEVEL_LABELS: Record<NonNullable<VariantProps<typeof classificationVariants>["level"]>, string> = {
  unclassified: "Không mật",
  confidential: "Mật",
  secret: "Tối mật",
  "top-secret": "Tuyệt mật",
}

// Map level to a CSS custom property background color
const LEVEL_BG: Record<NonNullable<VariantProps<typeof classificationVariants>["level"]>, string> = {
  unclassified: "var(--classification-unclassified)",
  confidential: "var(--classification-confidential)",
  secret: "var(--classification-secret)",
  "top-secret": "var(--classification-top-secret)",
}

export type ClassificationLevel = NonNullable<VariantProps<typeof classificationVariants>["level"]>

interface ClassificationBadgeProps
  extends Omit<React.HTMLAttributes<HTMLSpanElement>, "children">,
    VariantProps<typeof classificationVariants> {
  level: ClassificationLevel
}

export function ClassificationBadge({
  level,
  className,
  ...rest
}: ClassificationBadgeProps) {
  const label = LEVEL_LABELS[level]

  return (
    <span
      role="img"
      aria-label={`Mức độ bảo mật: ${label}`}
      style={{ backgroundColor: LEVEL_BG[level] }}
      className={cn(classificationVariants({ level }), className)}
      {...rest}
    >
      {label}
    </span>
  )
}
