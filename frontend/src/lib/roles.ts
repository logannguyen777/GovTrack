/**
 * frontend/src/lib/roles.ts
 *
 * Single source of truth for role metadata: labels, landing paths, and route
 * access matrix. Imported by sidebar, top-bar, role-switcher, login page, and
 * the internal layout route guard.
 *
 * Backend mirror: backend/src/models/enums.py Role enum.
 */

export const ROLE_VALUES = [
  "admin",
  "leader",
  "staff_intake",
  "staff_processor",
  "legal",
  "security",
  "officer",
  "public_viewer",
  "citizen",
] as const;

export type RoleValue = (typeof ROLE_VALUES)[number];

/** Vietnamese labels shown in sidebar, top-bar, and role badges. */
export const ROLE_LABELS: Record<string, string> = {
  admin: "Quản trị viên",
  leader: "Lãnh đạo",
  staff_intake: "Cán bộ tiếp nhận",
  staff_processor: "Chuyên viên xử lý",
  legal: "Pháp chế",
  security: "An ninh",
  officer: "Cán bộ",
  public_viewer: "Xem công khai",
  citizen: "Công dân",
};

/** Landing path each role should be redirected to after login. */
export const ROLE_LANDING: Record<string, string> = {
  admin: "/dashboard",
  leader: "/dashboard",
  staff_intake: "/intake",
  staff_processor: "/inbox",
  legal: "/consult",
  security: "/security",
  officer: "/inbox",
  public_viewer: "/portal",
  citizen: "/portal",
};

/**
 * Route → allowed roles matrix. Used by NAV_ITEMS filter and the (internal)
 * route guard. Keys match the first segment of the pathname (e.g. "/inbox").
 *
 * Order matters for longest-prefix match in canAccessRoute.
 */
export const ROUTE_ROLES: Array<{ prefix: string; roles: string[] }> = [
  { prefix: "/dashboard", roles: ["admin", "leader", "security"] },
  { prefix: "/intake", roles: ["admin", "leader", "staff_intake", "staff_processor", "security"] },
  { prefix: "/inbox", roles: ["admin", "leader", "staff_intake", "staff_processor", "legal", "security"] },
  { prefix: "/compliance", roles: ["admin", "leader", "staff_processor", "legal", "security"] },
  { prefix: "/consult", roles: ["admin", "leader", "staff_processor", "legal", "security"] },
  { prefix: "/documents", roles: ["admin", "leader", "staff_intake", "staff_processor", "legal", "security"] },
  { prefix: "/trace", roles: ["admin", "leader", "staff_processor", "legal", "security"] },
  { prefix: "/security", roles: ["admin", "security"] },
];

/** Return true if `role` can access the given `pathname`. */
export function canAccessRoute(role: string | undefined, pathname: string): boolean {
  if (!role) return false;
  const match = ROUTE_ROLES.find((r) => pathname === r.prefix || pathname.startsWith(r.prefix + "/"));
  if (!match) return true;
  return match.roles.includes(role);
}

/** Return the landing path for a role, falling back to /inbox. */
export function landingForRole(role: string | undefined): string {
  if (!role) return "/auth/login";
  return ROLE_LANDING[role] ?? "/inbox";
}
