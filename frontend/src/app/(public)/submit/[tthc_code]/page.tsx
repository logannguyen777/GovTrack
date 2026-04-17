"use client";

import { use, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { SubmitWizard } from "@/components/submit/submit-wizard";

function SubmitPageInner({ tthcCode }: { tthcCode: string }) {
  const searchParams = useSearchParams();
  const prefillId = searchParams.get("prefill");
  return <SubmitWizard tthcCode={tthcCode} prefillId={prefillId} />;
}

export default function SubmitPage({
  params,
}: {
  params: Promise<{ tthc_code: string }>;
}) {
  const { tthc_code } = use(params);

  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-2xl px-4 py-12">
          <div className="h-96 animate-pulse rounded-lg bg-[var(--bg-surface)]" />
        </div>
      }
    >
      <SubmitPageInner tthcCode={tthc_code} />
    </Suspense>
  );
}
