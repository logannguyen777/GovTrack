"use client";

import { useEffect, useCallback } from "react";
import { HelpCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useOnboardingStore } from "@/lib/stores/onboarding-store";
import { TOURS, type TourId } from "@/lib/tours";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface OnboardingTourProps {
  tourId: TourId;
  autoStart?: boolean;
  showButton?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function OnboardingTour({
  tourId,
  autoStart = false,
  showButton = true,
}: OnboardingTourProps) {
  const completed = useOnboardingStore((s) => s.completedTours.includes(tourId));
  const markDone = useOnboardingStore((s) => s.markTourDone);
  const steps = TOURS[tourId];

  const run = useCallback(async () => {
    // Dynamically import driver.js to avoid SSR issues
    const { driver } = await import("driver.js");

    const d = driver({
      showProgress: true,
      nextBtnText: "Tiếp",
      prevBtnText: "Trước",
      doneBtnText: "Hoàn tất",
      progressText: "{{current}}/{{total}}",
      steps: steps.map((s) => ({
        element: s.element,
        popover: {
          title: s.title,
          description: s.description,
          side: s.side ?? "bottom",
        },
      })),
      onDestroyed: () => markDone(tourId),
    });
    d.drive();
  }, [steps, tourId, markDone]);

  useEffect(() => {
    if (autoStart && !completed) {
      const t = setTimeout(() => void run(), 800);
      return () => clearTimeout(t);
    }
  }, [autoStart, completed, run]);

  if (!showButton) return null;

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => void run()}
      aria-label="Bắt đầu tour hướng dẫn"
    >
      <HelpCircle className="h-4 w-4 mr-1.5" aria-hidden="true" />
      Làm quen
    </Button>
  );
}
