/**
 * Build a URL for MetaBrainz OAuth authentication.
 * @param loginHint - The login hint to pass to MetaBrainz
 * @param next - Optional URL to redirect to after login (defaults to current page)
 * @returns The full authentication URL
 */
export default function buildAuthUrl(
  loginHint: "login" | "register",
  next?: string
): string {
  const params = new URLSearchParams({ login_hint: loginHint });
  const nextUrl = next ?? window.location.href;
  if (nextUrl) {
    params.set("next", nextUrl);
  }
  return `/login/musicbrainz/?${params.toString()}`;
}
