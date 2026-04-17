import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

export interface ConsultInboxItem {
  request_id: string;
  case_id: string;
  case_code: string;
  tthc_code: string;
  tthc_name: string;
  applicant_name: string;
  target_org_id: string;
  target_org_name: string;
  context_summary: string;
  main_question: string;
  sub_questions: string;
  deadline: string;
  urgency: string;
  status: string;
  created_at: string | null;
}

export const consultKeys = {
  inbox: (status: string) => ["consult-inbox", status] as const,
  caseRequests: (caseId: string) => ["consult-requests", caseId] as const,
};

export function useConsultInbox(status: string = "pending") {
  return useQuery<ConsultInboxItem[]>({
    queryKey: consultKeys.inbox(status),
    queryFn: () =>
      apiClient.get<ConsultInboxItem[]>(`/api/agents/consult/inbox`, { status }),
    refetchInterval: 15000,
  });
}

export interface ConsultOpinionBody {
  department_id: string;
  department_name: string;
  stance: "agree" | "disagree" | "abstain";
  opinion: string;
  citation: string[];
  confidence: number;
  author_name: string;
}

export function useSubmitConsultOpinion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { requestId: string; body: ConsultOpinionBody }) => {
      return apiClient.post<{ opinion_id: string }>(
        `/api/agents/consult/${args.requestId}/opinion`,
        args.body,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["consult-inbox"] });
    },
  });
}
