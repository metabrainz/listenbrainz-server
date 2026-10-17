import * as React from "react";
import { render, screen } from "@testing-library/react";

import {
  getRelIconLink,
  getStreamingServiceFromURL,
} from "../../src/album/utils";

describe("getStreamingServiceFromURL", () => {
  it("identifies services that have a custom icon", () => {
    const qobuz = getStreamingServiceFromURL(
      "https://open.qobuz.com/artist/12345"
    );
    expect(qobuz?.name).toEqual("Qobuz");
    expect(qobuz?.icon).toBeDefined();
  });

  it("returns the Tidal icon now that Font Awesome v7 provides it", () => {
    const tidal = getStreamingServiceFromURL(
      "https://tidal.com/browse/artist/678"
    );
    expect(tidal?.name).toEqual("Tidal");
    expect(tidal?.icon).toBeDefined();
  });

  it("returns a brand icon and colour where one exists", () => {
    const spotify = getStreamingServiceFromURL(
      "https://open.spotify.com/artist/1234"
    );
    expect(spotify?.name).toEqual("Spotify");
    expect(spotify?.icon).toBeDefined();
    expect(spotify?.color).toEqual("#1DB954");
  });

  it("matches subdomains but not lookalike domains", () => {
    expect(
      getStreamingServiceFromURL("https://music.apple.com/gb/artist/1")?.name
    ).toEqual("Apple Music");
    // A host that merely ends with the same letters must not match.
    expect(
      getStreamingServiceFromURL("https://nottidal.com/artist/1")
    ).toBeUndefined();
    expect(
      getStreamingServiceFromURL("https://evil-qobuz.com/artist/1")
    ).toBeUndefined();
  });

  it("anchors the TLD so a lookalike parent domain cannot match", () => {
    // amazon.evil.com is a subdomain of evil.com, not of amazon.
    expect(
      getStreamingServiceFromURL("https://amazon.evil.com/artist/1")
    ).toBeUndefined();
    expect(
      getStreamingServiceFromURL("https://music.amazon.co.jp/artist/1")?.name
    ).toEqual("Amazon Music");
    expect(
      getStreamingServiceFromURL("https://www.amazon.de/dp/B000")?.name
    ).toEqual("Amazon Music");
  });

  it("does not match a service name that only appears in the path", () => {
    // A whole-URL regex would wrongly call this Tidal.
    expect(
      getStreamingServiceFromURL("https://example.com/artist/tidal-tribute")
    ).toBeUndefined();
  });

  it("returns undefined for unknown services and unparseable URLs", () => {
    expect(getStreamingServiceFromURL("https://example.com/x")).toBeUndefined();
    expect(getStreamingServiceFromURL("not a url")).toBeUndefined();
    expect(getStreamingServiceFromURL("")).toBeUndefined();
  });
});

describe("getRelIconLink", () => {
  it("names the streaming service in the link title", () => {
    // Before LB-1992 this read "streaming", which told the reader nothing
    // about where the icon led.
    render(getRelIconLink("streaming", "https://open.qobuz.com/artist/12345"));
    expect(screen.getByTitle("Qobuz")).toBeInTheDocument();
  });

  it("falls back to the relationship name for an unknown service", () => {
    render(getRelIconLink("streaming", "https://example.com/artist/1"));
    expect(screen.getByTitle("streaming")).toBeInTheDocument();
  });

  it("leaves other relationship types alone", () => {
    render(getRelIconLink("lyrics", "https://genius.com/artists/x"));
    expect(screen.getByTitle("lyrics")).toBeInTheDocument();
  });
});
