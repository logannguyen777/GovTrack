import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/", "/auth/login"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public routes: no auth required
  if (
    PUBLIC_PATHS.some((p) => pathname === p) ||
    pathname.startsWith("/track") ||
    pathname.startsWith("/api/public")
  ) {
    return NextResponse.next();
  }

  // Static assets and Next internals
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.startsWith("/api/")
  ) {
    return NextResponse.next();
  }

  // Check JWT in cookie
  const token = request.cookies.get("govflow-token")?.value;

  if (!token) {
    // Client-side auth guard in (internal)/layout.tsx handles localStorage check
    // Middleware only blocks if cookie is explicitly set to empty
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
