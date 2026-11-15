import { getMissingDataLinks } from "../../../src/settings/link-listens/utils";

const row: UnlinkedListens = {
  artist_name: "Example artist",
  recording_name: "Example song",
  release_name: "Example album",
  listened_at: "2026-11-04T10:00:00.000Z",
  recording_msid: "c0f95f14-f222-4a1d-9068-9b092716ef94",
};
const trackId = "2TZIQDtf2H4bazKfBa6I4T";
const albumId = "2HaqZjwdtGVdDsoenjoJrT";
const spotifyAlbum = `https://open.spotify.com/album/${albumId}`;

function links(
  additional_info: MissingDataAdditionalInfo,
  release_name = row.release_name
) {
  return getMissingDataLinks({ ...row, release_name, additional_info });
}

function expectAlbum(href: string, service: string) {
  const result = links({ origin_url: href });
  expect(result.map((link) => link.label)).toEqual([
    `Open album in ${service}`,
    `Look up album in Harmony (${service})`,
    `Look up album in SAMBL (${service})`,
  ]);
  expect(result[0].href).toBe(href);
  expect(
    new URL(result[1].href).origin + new URL(result[1].href).pathname
  ).toBe("https://harmony.pulsewidth.org.uk/release");
  expect(
    new URL(result[2].href).origin + new URL(result[2].href).pathname
  ).toBe("https://sambl.lioncat6.com/seed");
  result.slice(1).forEach((link) => {
    expect(new URL(link.href).searchParams.getAll("url")).toEqual([href]);
  });
}

describe("getMissingDataLinks", () => {
  it.each([undefined, null, {}])(
    "leaves legacy metadata %p unlinked",
    (additional_info) => {
      expect(getMissingDataLinks({ ...row, additional_info })).toEqual([]);
    }
  );

  it("orders direct Spotify links before album tools and removes origin duplicates", () => {
    const input = Object.freeze({
      ...row,
      additional_info: Object.freeze({
        spotify_id: `https://open.spotify.com/intl-de/track/${trackId}?si=tracking`,
        spotify_album_id: albumId,
        origin_url: `https://open.spotify.com/track/${trackId}`,
      }),
    });
    expect(
      getMissingDataLinks(input).map(({ label, href }) => [label, href])
    ).toEqual([
      ["Open in Spotify", `https://open.spotify.com/track/${trackId}`],
      ["Open album in Spotify", spotifyAlbum],
      [
        "Look up album in Harmony (Spotify)",
        `https://harmony.pulsewidth.org.uk/release?url=${encodeURIComponent(
          spotifyAlbum
        )}`,
      ],
      [
        "Look up album in SAMBL (Spotify)",
        `https://sambl.lioncat6.com/seed?url=${encodeURIComponent(
          spotifyAlbum
        )}`,
      ],
    ]);
    expect(input.additional_info.spotify_album_id).toBe(albumId);
  });

  it.each([
    [spotifyAlbum, "Spotify"],
    ["https://music.apple.com/gb/album/1566636556", "Apple Music"],
    ["https://example-artist.bandcamp.com/album/example-album", "Bandcamp"],
    ["https://www.deezer.com/album/123456", "Deezer"],
    ["https://listen.tidal.com/album/123456", "Tidal"],
  ])("keeps album %s visible alongside supported tools", expectAlbum);

  it.each([
    [
      "https://youtu.be/dQw4w9WgXcQ?t=10",
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ],
    [
      "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ],
    [
      "https://www.youtube.com/shorts/dQw4w9WgXcQ",
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ],
    [
      "https://youtube.com/embed/dQw4w9WgXcQ",
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ],
  ])("normalizes video %s without album tools", (origin_url, href) => {
    expect(links({ origin_url, youtube_id: "dQw4w9WgXcQ" }, null)).toEqual([
      expect.objectContaining({
        label: "Open in YouTube",
        href,
        kind: "source",
      }),
    ]);
  });

  it("keeps an Apple regional song and its distinct album, including tool parameters", () => {
    const result = links({
      origin_url:
        "https://music.apple.com/gb/album/taste-of-love/1566636556?i=1566636563&at=tracking#fragment",
      apple_music_id: "1566636563",
      apple_album_id: "1566636556",
    });
    expect(result.map((link) => link.label)).toEqual([
      "Open in Apple Music",
      "Open album in Apple Music",
      "Look up album in Harmony (Apple Music)",
      "Look up album in SAMBL (Apple Music)",
    ]);
    expect(result[0].href).toBe(
      "https://music.apple.com/gb/album/taste-of-love/1566636556?i=1566636563"
    );
    expect(result[1].href).toBe(
      "https://music.apple.com/gb/album/taste-of-love/1566636556"
    );
    expect(new URL(result[2].href).searchParams.get("url")).toBe(
      result[1].href
    );
    expect(new URL(result[3].href).searchParams.get("url")).toBe(
      result[1].href
    );
  });

  it("constructs proven numeric Apple album and album-plus-song routes", () => {
    const result = links({
      apple_album_id: "1566636556",
      apple_music_id: "1566636563",
    });
    expect(result[0].href).toBe(
      "https://music.apple.com/us/album/1566636556?i=1566636563"
    );
    expect(result[1].href).toBe("https://music.apple.com/us/album/1566636556");
    expect(result).toHaveLength(4);
  });

  it.each(["apple_album_id", "origin_url"] as const)(
    "constructs an Apple album-plus-song route from a URL in %s",
    (field) => {
      const album =
        "https://music.apple.com/gb/album/taste-of-love/1566636556";
      const result = links({
        [field]: `${album}?at=tracking#fragment`,
        apple_music_id: "1566636563",
      });
      expect(result.map(({ label, href }) => [label, href])).toEqual([
        ["Open in Apple Music", `${album}?i=1566636563`],
        ["Open album in Apple Music", album],
        [
          "Look up album in Harmony (Apple Music)",
          `https://harmony.pulsewidth.org.uk/release?url=${encodeURIComponent(
            album
          )}`,
        ],
        [
          "Look up album in SAMBL (Apple Music)",
          `https://sambl.lioncat6.com/seed?url=${encodeURIComponent(album)}`,
        ],
      ]);
    }
  );

  it("does not guess a standalone numeric Apple song URL or its album", () => {
    expect(links({ apple_music_id: "1566636563" })).toEqual([
      expect.objectContaining({
        kind: "search",
        label: "Search Apple Music for album",
      }),
    ]);
    expect(
      links(
        {
          origin_url: "https://music.apple.com/gb/song/alcohol-free/1566636563",
        },
        null
      )
    ).toEqual([
      expect.objectContaining({
        kind: "source",
        href: "https://music.apple.com/gb/song/alcohol-free/1566636563",
      }),
    ]);
  });

  it.each([
    { apple_album_id: "https://music.apple.com/gb/song/example/1566636563" },
    { apple_music_id: "https://music.apple.com/gb/album/1566636556" },
    { spotify_album_id: `https://open.spotify.com/track/${trackId}` },
    { spotify_id: spotifyAlbum },
  ])("does not reinterpret a dedicated resource field %p", (metadata) => {
    expect(links(metadata)).toEqual([]);
  });

  it("uses the provided Apple album identity rather than a different origin edition", () => {
    const result = links({
      origin_url: "https://music.apple.com/gb/album/269572838",
      apple_album_id: "1566636556",
      apple_music_id: "1566636563",
    });
    expect(result[0].href).toBe(
      "https://music.apple.com/gb/album/1566636556?i=1566636563"
    );
    expect(result.filter((link) => link.kind === "album")).toHaveLength(2);
  });

  it("deduplicates generated and submitted regionless Apple album identities", () => {
    const result = links({
      origin_url: "https://music.apple.com/album/1566636556",
      apple_album_id: "1566636556",
      apple_music_id: "1566636563",
    });
    expect(result).toHaveLength(4);
    expect(result[0].href).toBe(
      "https://music.apple.com/album/1566636556?i=1566636563"
    );
  });

  it("does not invent an album-plus-song URL from ambiguous Apple albums", () => {
    const result = links({
      origin_url: "https://music.apple.com/gb/album/269572838",
      apple_music_id:
        "https://music.apple.com/gb/album/1566636556?i=1566636563",
    });
    expect(result.filter((link) => link.kind === "source")).toHaveLength(1);
    expect(result.filter((link) => link.kind === "album")).toHaveLength(2);
  });

  it.each([
    [
      "https://youtu.be/dQw4w9WgXcQ",
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ],
    [
      "https://music.apple.com/gb/song/example/1566636563",
      "https://music.apple.com/gb/song/example/1566636563",
    ],
  ])("retains valid dedicated song URL %s", (href, canonical) => {
    const metadata = href.includes("apple.com")
      ? { apple_music_id: href }
      : { youtube_id: href };
    expect(links(metadata, null)[0].href).toBe(canonical);
  });

  it.each([
    [
      "https://deezer.com/en/track/123456",
      "https://www.deezer.com/track/123456",
      "Deezer",
    ],
    [
      "https://tidal.com/browse/track/123456",
      "https://listen.tidal.com/track/123456",
      "Tidal",
    ],
    [
      "https://example-artist.bandcamp.com/track/example-song",
      "https://example-artist.bandcamp.com/track/example-song",
      "Bandcamp",
    ],
    [
      "https://www.soundcloud.com/example-artist/example-song?utm_source=tracking",
      "https://soundcloud.com/example-artist/example-song",
      "SoundCloud",
    ],
  ])("does not invent an album from track %s", (origin_url, href, service) => {
    expect(links({ origin_url }, null)).toEqual([
      expect.objectContaining({
        label: `Open in ${service}`,
        href,
        kind: "source",
      }),
    ]);
  });

  it("keeps SoundCloud sets local and does not call them tracks or importable albums", () => {
    const result = links(
      { origin_url: "https://soundcloud.com/example-artist/sets/example-set" },
      null
    );
    expect(result).toHaveLength(2);
    expect(result[0].kind).toBe("source");
    expect(result[1].label).toBe("Search SoundCloud for track");
  });

  it("keeps distinct independently supplied album identities", () => {
    const result = links({
      spotify_album_id: albumId,
      origin_url: "https://open.spotify.com/album/0123456789012345678901",
    });
    expect(result.filter((link) => link.kind === "album")).toHaveLength(2);
    expect(result.filter((link) => link.kind === "harmony")).toHaveLength(2);
    expect(new Set(result.map((link) => link.key)).size).toBe(result.length);
  });

  it("allows a source album search beside a track and an unrelated video", () => {
    const result = links({
      spotify_id: trackId,
      youtube_id: "dQw4w9WgXcQ",
      music_service: " SPOTIFY.COM ",
      music_service_name: "Spotify",
    });
    expect(result.filter((link) => link.kind === "search")).toEqual([
      expect.objectContaining({
        label: "Search Spotify for album",
        href:
          "https://open.spotify.com/search/Example%20artist%20Example%20album",
      }),
    ]);
  });

  it.each([
    { music_service: "unknown.test", spotify_id: trackId },
    { music_service_name: "unknown", spotify_id: trackId },
    {
      music_service: "spotify.com",
      music_service_name: "YouTube",
      spotify_id: trackId,
    },
    {
      music_service: "spotify.com",
      music_service_name: "unknown",
      spotify_id: trackId,
    },
    { spotify_id: trackId, youtube_id: "dQw4w9WgXcQ" },
    { music_service: "tidal.com" },
  ])("omits uncertain or unsupported searches for %p", (metadata) => {
    expect(links(metadata).filter((link) => link.kind === "search")).toEqual(
      []
    );
  });

  it.each([
    ["Spotify", "https://open.spotify.com/search/"],
    ["YouTube Music", "https://www.youtube.com/results?search_query="],
    ["iTunes", "https://music.apple.com/us/search?term="],
    ["Deezer", "https://www.deezer.com/search/"],
    ["Bandcamp", "https://bandcamp.com/search?q="],
    ["SoundCloud", "https://soundcloud.com/search?q="],
  ])("encodes a source-only %s search", (music_service_name, prefix) => {
    const input = {
      ...row,
      artist_name: " Björk  & / ",
      release_name: " Album ? ",
      additional_info: { music_service_name },
    };
    const result = getMissingDataLinks(input);
    expect(result).toHaveLength(1);
    expect(result[0].href.startsWith(prefix)).toBe(true);
    const url = new URL(result[0].href);
    const query =
      url.searchParams.get("q") ??
      url.searchParams.get("term") ??
      url.searchParams.get("search_query") ??
      decodeURIComponent(url.pathname.split("/search/")[1]);
    expect(query).toBe("Björk & / Album ?");
    expect(input.artist_name).toBe(" Björk  & / ");
  });

  it("uses track fallback only without a release or known source track", () => {
    expect(links({ music_service: "bandcamp.com" }, "  ")[0].label).toBe(
      "Search Bandcamp for track"
    );
    expect(
      links({ spotify_id: trackId }, null).filter(
        (link) => link.kind === "search"
      )
    ).toEqual([]);
    expect(
      links(
        { music_service: "spotify.com", youtube_id: "dQw4w9WgXcQ" },
        null
      ).at(-1)?.label
    ).toBe("Search Spotify for track");
  });

  it.each([
    "javascript:alert(1)",
    "data:text/html,hello",
    "http://open.spotify.com/track/2TZIQDtf2H4bazKfBa6I4T",
    "//open.spotify.com/track/2TZIQDtf2H4bazKfBa6I4T",
    "/track/2TZIQDtf2H4bazKfBa6I4T",
    "not a URL",
    "https://user:password@open.spotify.com/track/2TZIQDtf2H4bazKfBa6I4T",
    "https://open.spotify.com:444/track/2TZIQDtf2H4bazKfBa6I4T",
    "https://open.spotify.com.evil.test/track/2TZIQDtf2H4bazKfBa6I4T",
    "https://notspotify.com/album/2HaqZjwdtGVdDsoenjoJrT",
    "https://example.test/spotify.com?url=soundcloud.com",
    "https://open.spotify.com/artist/2TZIQDtf2H4bazKfBa6I4T",
    "https://open.spotify.com/track/short",
    "https://www.youtube.com/watch?v=short",
    "https://music.apple.com/gb/artist/example/123",
    "https://bandcamp.com/album/example",
    "https://www.bandcamp.com/album/example",
    "https://evil.artist.bandcamp.com/album/example",
    "https://example-artist.bandcamp.com/",
    "https://soundcloud.com/search?q=example",
    "https://soundcloud.com/example/sets",
    "https://soundcloud.com/discover/sets",
    "https://www.deezer.com/artist/123",
    "https://tidal.com/album/123/extra",
  ])("rejects unsafe or unsupported origin %s", (origin_url) => {
    expect(links({ origin_url })).toEqual([]);
  });

  it.each([
    42,
    true,
    [],
    { spotify_id: 42, origin_url: false },
    { spotify_id: [], music_service: {} },
  ])("ignores invalid runtime metadata %p", (additional_info) => {
    const input: UnlinkedListens = JSON.parse(
      JSON.stringify({ ...row, additional_info })
    );
    expect(getMissingDataLinks(input)).toEqual([]);
  });
});
