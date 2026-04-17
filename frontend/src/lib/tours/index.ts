export type TourStep = {
  element: string;
  title: string;
  description: string;
  side?: "top" | "bottom" | "left" | "right";
};

export type TourId =
  | "citizen-portal"
  | "officer-inbox"
  | "leader-dashboard"
  | "trace-viewer"
  | "compliance-detail";

import { CITIZEN_PORTAL_TOUR } from "./citizen-portal";
import { OFFICER_INBOX_TOUR } from "./officer-inbox";
import { LEADER_DASHBOARD_TOUR } from "./leader-dashboard";
import { TRACE_VIEWER_TOUR } from "./trace-viewer";
import { COMPLIANCE_DETAIL_TOUR } from "./compliance-detail";

export const TOURS: Record<TourId, TourStep[]> = {
  "citizen-portal": CITIZEN_PORTAL_TOUR,
  "officer-inbox": OFFICER_INBOX_TOUR,
  "leader-dashboard": LEADER_DASHBOARD_TOUR,
  "trace-viewer": TRACE_VIEWER_TOUR,
  "compliance-detail": COMPLIANCE_DETAIL_TOUR,
};
