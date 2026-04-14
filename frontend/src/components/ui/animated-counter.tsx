"use client"

import { useEffect } from "react"
import { useMotionValue, useSpring, useTransform, motion } from "framer-motion"

interface AnimatedCounterProps {
  value: number
  suffix?: string
}

// Spring config tuned to the emphasis transition (400ms, ease-out-quart)
// stiffness/damping chosen so the spring settles near 400ms
const SPRING_CONFIG = {
  stiffness: 80,
  damping: 18,
  mass: 1,
}

export function AnimatedCounter({ value, suffix }: AnimatedCounterProps) {
  const motionValue = useMotionValue(0)
  const spring = useSpring(motionValue, SPRING_CONFIG)
  const display = useTransform(spring, (latest) => Math.round(latest).toLocaleString("vi-VN"))

  useEffect(() => {
    motionValue.set(value)
  }, [motionValue, value])

  return (
    <span className="font-mono tabular-nums">
      <motion.span>{display}</motion.span>
      {suffix && <span>{suffix}</span>}
    </span>
  )
}
