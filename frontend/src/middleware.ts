import { NextRequest, NextResponse } from "next/server";
import { jwtDecode } from "jwt-decode";

// ---------------------------------------------------------------------------
// Route categorisation
// ---------------------------------------------------------------------------

/** Paths that never require authentication. */
const PUBLIC_PATH_PREFIXES = [
  "/portal",
  "/track",
  "/submit",
  "/assistant",
  "/permission-demo",
  "/api/public",
];

/** Always skip — static assets + Next.js internals + SEO files. */
const SKIP_PREFIXES = [
  "/_next",
  "/favicon",
  "/api/",
];

/** Exact paths that always bypass middleware (SEO, manifests, well-known). */
const SKIP_EXACT = new Set([
  "/sitemap.xml",
  "/robots.txt",
  "/manifest.json",
  "/sw.js",
  "/icon.svg",
  "/icon.png",
  "/apple-touch-icon.png",
]);

/** Auth-flow paths (login page etc.) — skip auth check. */
const AUTH_PREFIXES = ["/auth"];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface JwtPayload {
  exp?: number;
  sub?: string;
  role?: string;
}

function isExpired(token: string): boolean {
  try {
    const payload = jwtDecode<JwtPayload>(token);
    if (typeof payload.exp !== "number") return false; // no exp → treat valid
    return payload.exp * 1000 < Date.now();
  } catch {
    return true; // malformed token → treat as expired
  }
}

// ---------------------------------------------------------------------------
// Middleware
// ---------------------------------------------------------------------------

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 1. Always skip Next.js internals, raw API routes, SEO/well-known files.
  if (
    SKIP_EXACT.has(pathname) ||
    SKIP_PREFIXES.some((p) => pathname.startsWith(p)) ||
    pathname.startsWith("/.well-known/")
  ) {
    return NextResponse.next();
  }

  // 2. Skip auth pages (login, etc.).
  if (AUTH_PREFIXES.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // 3. Skip public routes — no auth required.
  if (
    pathname === "/" ||
    PUBLIC_PATH_PREFIXES.some((p) => pathname.startsWith(p))
  ) {
    return NextResponse.next();
  }

  // 4. All remaining paths require a valid, non-expired JWT.
  //    Token is stored in localStorage (client-side only), so the middleware
  //    reads it from a cookie that the client sets as a mirror.
  //    If the cookie is absent or expired → redirect to login.
  const token = request.cookies.get("govflow-token")?.value;

  if (!token || isExpired(token)) {
    const next = encodeURIComponent(pathname + request.nextUrl.search);
    return NextResponse.redirect(
      new URL(`/auth/login?next=${next}`, request.url),
    );
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
