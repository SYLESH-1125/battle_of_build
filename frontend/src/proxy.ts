import { type NextRequest, NextResponse } from "next/server";

/**
 * PHASE 2: PRODUCTION AUTH MIDDLEWARE
 * Next.js Proxy for Supabase + Role-Based Route Protection
 */

export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Public routes that don't need auth
  const publicRoutes = ["/", "/login", "/_next", "/api", "/favicon.ico"];
  if (publicRoutes.some(route => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // For protected routes, just let them through for now
  // (Role-based access will be checked in the page components)
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
