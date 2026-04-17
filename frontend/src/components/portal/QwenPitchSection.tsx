"use client";

import { PitchDeck } from "./PitchDeck";

export default function QwenPitchSection() {
  return (
    <section
      className="w-full bg-gradient-to-b from-slate-50/50 to-white py-16"
      aria-labelledby="pitch-deck-heading"
    >
      <div className="mx-auto max-w-6xl px-4">
        <div className="mb-8 text-center">
          <span className="inline-flex items-center gap-1 rounded-full border border-[#5B5BD6]/30 bg-[#5B5BD6]/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-[#5B5BD6]">
            powered by Qwen3 · Alibaba Cloud Model Studio
          </span>
          <h2
            id="pitch-deck-heading"
            className="mt-3 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl"
          >
            3-minute pitch
          </h2>
          <p className="mx-auto mt-2 max-w-2xl text-slate-600">
            Kịch bản 14 slide tự chuyển · bấm ← / → để điều hướng, hoặc để tự chạy.
          </p>
        </div>
        <PitchDeck />
      </div>
    </section>
  );
}
