import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import createIntlMiddleware from "next-intl/middleware";

const locales = ["en", "ar"];
const defaultLocale = "en";

const intlMiddleware = createIntlMiddleware({
  locales,
  defaultLocale,
  localePrefix: "never",
});

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isAuthPage =
    pathname.startsWith("/login") ||
    pathname.startsWith("/register") ||
    pathname.startsWith("/invitations/accept");

  const isStaticAsset =
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname === "/favicon.ico";

  if (isStaticAsset) {
    return NextResponse.next();
  }

  // Intl middleware must be returned to provide locale context for getLocale()
  const intlResponse = intlMiddleware(request);
  if (!intlResponse) {
    return NextResponse.next();
  }

  const token = request.cookies.get("accessToken");

  if (!token && !isAuthPage) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const hasDesktopCallback = request.nextUrl.searchParams.has("desktop_callback");

  if (token && isAuthPage && !hasDesktopCallback) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return intlResponse;
}
