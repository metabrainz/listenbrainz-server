import buildAuthUrl from "../../src/utils/auth";

describe("buildAuthUrl", () => {
  it("builds an auth URL using the current page as the default next URL", () => {
    const url = new URL(buildAuthUrl("login"), window.location.origin);

    expect(url.pathname).toBe("/login/musicbrainz/");
    expect(url.searchParams.get("login_hint")).toBe("login");
    expect(url.searchParams.get("next")).toBe(window.location.href);
  });

  it("uses the explicit next URL when provided", () => {
    const url = new URL(
      buildAuthUrl("register", "/feed/"),
      window.location.origin
    );

    expect(url.pathname).toBe("/login/musicbrainz/");
    expect(url.searchParams.get("login_hint")).toBe("register");
    expect(url.searchParams.get("next")).toBe("/feed/");
  });
});
