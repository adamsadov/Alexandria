// middleware.js
import { NextResponse } from "next/server";

// Pages that need a signed-in user. The API enforces auth on its own; this
// only saves a round trip by sending signed-out visitors to the sign-in page.
const protectedRoutes = ["/club", "/profile", "/shelf", "/journals"];
// Exact matches only (e.g. /shelves/<username> stays public).
const protectedExact = ["/shelves"];

export function middleware(req) {
  const path = req.nextUrl.pathname;
  const isProtected = protectedRoutes.some(
    (route) => path === route || path.startsWith(`${route}/`)
  ) || protectedExact.includes(path);
  if (!isProtected) return NextResponse.next();

  // Django's session cookie, set by allauth at login. Its presence is only a
  // hint (it may be expired); Django validates it on every API request.
  if (req.cookies.has("sessionid")) return NextResponse.next();

  const signIn = new URL("/auth/sign-in", req.url);
  signIn.searchParams.set("next", path + req.nextUrl.search);
  return NextResponse.redirect(signIn);
}

export const config = {
  matcher: [
    "/((?!_next|_allauth|api|media|[^?]*\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
  ],
};
