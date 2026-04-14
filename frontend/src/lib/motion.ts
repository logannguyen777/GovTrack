import type { Variants, Transition } from "framer-motion";

export const transitions = {
  micro: { duration: 0.15, ease: [0.25, 1, 0.5, 1] } satisfies Transition,
  default: { duration: 0.25, ease: [0.25, 1, 0.5, 1] } satisfies Transition,
  emphasis: { duration: 0.4, ease: [0.25, 1, 0.5, 1] } satisfies Transition,
  spring: { type: "spring", stiffness: 300, damping: 25 } satisfies Transition,
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: transitions.default },
};

export const slideUp: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: transitions.default },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1, transition: transitions.default },
};

export const staggerContainer: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05 } },
};

export const redactedReveal: Variants = {
  masked: { filter: "blur(8px)", opacity: 0.6 },
  revealed: { filter: "blur(0px)", opacity: 1, transition: transitions.emphasis },
};
