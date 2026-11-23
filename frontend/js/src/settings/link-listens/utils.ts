export type MissingDataLink = {
  key: string;
  kind: "source" | "album" | "harmony" | "sambl" | "search";
  service: string;
  label: string;
  href: string;
};

type Service =
  | "Spotify"
  | "YouTube"
  | "Apple Music"
  | "Bandcamp"
  | "Deezer"
  | "Tidal"
  | "SoundCloud";
type Resource = {
  service: Service;
  kind: "track" | "album" | "set";
  id: string;
  href: string;
  storefront?: string;
};

const spotifyId = /^[A-Za-z0-9]{22}$/;
const youtubeId = /^[A-Za-z0-9_-]{11}$/;
const numericId = /^[1-9][0-9]*$/;
const serviceDomains = new Map<string, Service>([
  ["spotify.com", "Spotify"],
  ["open.spotify.com", "Spotify"],
  ["youtube.com", "YouTube"],
  ["music.youtube.com", "YouTube"],
  ["music.apple.com", "Apple Music"],
  ["itunes.apple.com", "Apple Music"],
  ["bandcamp.com", "Bandcamp"],
  ["deezer.com", "Deezer"],
  ["tidal.com", "Tidal"],
  ["soundcloud.com", "SoundCloud"],
]);
const serviceNames = new Map<string, Service>([
  ["spotify", "Spotify"],
  ["youtube", "YouTube"],
  ["youtube music", "YouTube"],
  ["apple music", "Apple Music"],
  ["itunes", "Apple Music"],
  ["bandcamp", "Bandcamp"],
  ["deezer", "Deezer"],
  ["tidal", "Tidal"],
  ["soundcloud", "SoundCloud"],
]);

function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function parseURL(value: unknown): URL | undefined {
  const input = text(value);
  if (
    !input ||
    input.includes("\\") ||
    Array.from(input).some(
      (character) =>
        character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127
    )
  )
    return undefined;
  try {
    const url = new URL(input);
    if (
      url.protocol === "https:" &&
      !url.username &&
      !url.password &&
      !url.port
    )
      return url;
  } catch {
    return undefined;
  }
  return undefined;
}

function parseResource(value: unknown): Resource[] {
  const url = parseURL(value);
  if (!url) return [];
  const { hostname, pathname } = url;
  if (hostname === "open.spotify.com") {
    const match = pathname.match(
      /^\/(?:intl-[a-z]{2}(?:-[a-z]{2})?\/)?(track|album)\/([A-Za-z0-9]{22})\/?$/i
    );
    if (match)
      return [
        {
          service: "Spotify",
          kind: match[1].toLowerCase() as "track" | "album",
          id: match[2],
          href: `https://open.spotify.com/${match[1].toLowerCase()}/${
            match[2]
          }`,
        },
      ];
  }
  if (
    [
      "youtube.com",
      "www.youtube.com",
      "music.youtube.com",
      "youtu.be",
    ].includes(hostname)
  ) {
    let id;
    if (hostname === "youtu.be")
      id = pathname.match(/^\/([A-Za-z0-9_-]{11})\/?$/)?.[1];
    else if (pathname === "/watch" && url.searchParams.getAll("v").length === 1)
      id = url.searchParams.get("v");
    else
      id = pathname.match(/^\/(?:shorts|embed)\/([A-Za-z0-9_-]{11})\/?$/)?.[1];
    if (id && youtubeId.test(id))
      return [
        {
          service: "YouTube",
          kind: "track",
          id,
          href: `https://www.youtube.com/watch?v=${id}`,
        },
      ];
  }
  if (hostname === "music.apple.com") {
    const match = pathname.match(
      /^\/(?:([a-z]{2})\/)?(song|album)\/(?:[^/]+\/)?([1-9][0-9]*)\/?$/
    );
    if (match) {
      const storefront = match[1];
      const href = `https://music.apple.com${pathname.replace(/\/$/, "")}`;
      if (match[2] === "song")
        return [
          {
            service: "Apple Music",
            kind: "track",
            id: match[3],
            href,
            storefront,
          },
        ];
      const album: Resource = {
        service: "Apple Music",
        kind: "album",
        id: match[3],
        href,
        storefront,
      };
      const song = url.searchParams.get("i");
      if (
        song &&
        numericId.test(song) &&
        url.searchParams.getAll("i").length === 1
      ) {
        return [
          {
            service: "Apple Music",
            kind: "track",
            id: song,
            href: `${href}?i=${song}`,
            storefront,
          },
          album,
        ];
      }
      return [album];
    }
  }
  if (
    [
      "deezer.com",
      "www.deezer.com",
      "tidal.com",
      "www.tidal.com",
      "listen.tidal.com",
    ].includes(hostname)
  ) {
    const deezer = hostname === "deezer.com" || hostname === "www.deezer.com";
    const match = pathname.match(
      deezer
        ? /^\/(?:[a-z]{2}\/)?(track|album)\/([1-9][0-9]*)\/?$/
        : /^\/(?:browse\/)?(track|album)\/([1-9][0-9]*)\/?$/
    );
    if (match)
      return [
        {
          service: deezer ? "Deezer" : "Tidal",
          kind: match[1] as "track" | "album",
          id: match[2],
          href: `https://${deezer ? "www.deezer.com" : "listen.tidal.com"}/${
            match[1]
          }/${match[2]}`,
        },
      ];
  }
  const bandcampArtist = hostname.match(
    /^([a-z0-9](?:[a-z0-9-]*[a-z0-9])?)\.bandcamp\.com$/
  )?.[1];
  if (
    bandcampArtist &&
    ![
      "www",
      "daily",
      "discover",
      "help",
      "support",
      "blog",
      "api",
      "artists",
    ].includes(bandcampArtist)
  ) {
    const match = pathname.match(/^\/(track|album)\/([a-z0-9-]+)\/?$/);
    if (match)
      return [
        {
          service: "Bandcamp",
          kind: match[1] as "track" | "album",
          id: `${hostname}/${match[2]}`,
          href: `https://${hostname}/${match[1]}/${match[2]}`,
        },
      ];
  }
  if (["soundcloud.com", "www.soundcloud.com"].includes(hostname)) {
    const match = pathname.match(
      /^\/([A-Za-z0-9_-]+)\/(?:sets\/)?([A-Za-z0-9_-]+)\/?$/
    );
    const reserved = [
      "search",
      "discover",
      "stream",
      "you",
      "upload",
      "settings",
      "messages",
      "charts",
      "stations",
      "premium",
      "terms",
      "pages",
      "tracks",
      "albums",
      "reposts",
      "popular-tracks",
      "following",
      "followers",
      "likes",
      "sets",
    ];
    if (match && !reserved.includes(match[1]) && !reserved.includes(match[2])) {
      const kind = pathname.split("/")[2] === "sets" ? "set" : "track";
      return [
        {
          service: "SoundCloud",
          kind,
          id: pathname.replace(/\/$/, ""),
          href: `https://soundcloud.com${pathname.replace(/\/$/, "")}`,
        },
      ];
    }
  }
  return [];
}

function sourceService(
  info: MissingDataAdditionalInfo,
  origin: Resource[],
  identities: Service[]
): Service | undefined {
  const domain = text(info.music_service).toLowerCase();
  const name = text(info.music_service_name).toLowerCase();
  const domainService = serviceDomains.get(domain);
  const nameService = serviceNames.get(name);
  if (domain) {
    if (!domainService || (name && nameService !== domainService))
      return undefined;
    return domainService;
  }
  if (name) return nameService;
  if (origin.length) return origin[0].service;
  const services = new Set(identities);
  return services.size === 1 ? identities[0] : undefined;
}

function searchURL(
  service: Service,
  query: string,
  storefront: string
): string | undefined {
  if (service === "Tidal") return undefined;
  if (service === "Spotify")
    return `https://open.spotify.com/search/${encodeURIComponent(query)}`;
  if (service === "Deezer")
    return `https://www.deezer.com/search/${encodeURIComponent(query)}`;
  let href: string;
  let parameter: string;
  switch (service) {
    case "YouTube":
      href = "https://www.youtube.com/results";
      parameter = "search_query";
      break;
    case "Apple Music":
      href = `https://music.apple.com/${storefront}/search`;
      parameter = "term";
      break;
    case "Bandcamp":
      href = "https://bandcamp.com/search";
      parameter = "q";
      break;
    default:
      href = "https://soundcloud.com/search";
      parameter = "q";
  }
  const url = new URL(href);
  url.searchParams.set(parameter, query);
  return url.href;
}

/** Build links from this record only; never forward submitted URLs to shared players. */
export function getMissingDataLinks(row: UnlinkedListens): MissingDataLink[] {
  const info = row.additional_info;
  if (!info || typeof info !== "object" || Array.isArray(info)) return [];
  const origin = parseResource(info.origin_url);
  const resources = [...origin];
  const identities: Service[] = [];
  const addDedicated = (
    value: unknown,
    service: Service,
    kind: "track" | "album",
    pattern: RegExp,
    base: string
  ) => {
    const input = text(value);
    const parsed = parseResource(input).filter(
      (resource) => resource.service === service && resource.kind === kind
    );
    if (parsed.length) {
      resources.push(...parsed);
      identities.push(service);
    } else if (pattern.test(input)) {
      identities.push(service);
      if (
        !resources.some(
          (resource) =>
            resource.service === service &&
            resource.kind === kind &&
            resource.id === input
        )
      ) {
        resources.push({ service, kind, id: input, href: `${base}${input}` });
      }
    }
  };
  addDedicated(
    info.spotify_id,
    "Spotify",
    "track",
    spotifyId,
    "https://open.spotify.com/track/"
  );
  addDedicated(
    info.spotify_album_id,
    "Spotify",
    "album",
    spotifyId,
    "https://open.spotify.com/album/"
  );
  addDedicated(
    info.youtube_id,
    "YouTube",
    "track",
    youtubeId,
    "https://www.youtube.com/watch?v="
  );
  const appleSongURL = parseResource(info.apple_music_id);
  const appleAlbumURL = parseResource(info.apple_album_id).filter(
    (resource) =>
      resource.service === "Apple Music" && resource.kind === "album"
  );
  const appleURLs = [
    ...appleSongURL.filter(
      (resource) =>
        resource.service === "Apple Music" &&
        appleSongURL.some((song) => song.kind === "track")
    ),
    ...appleAlbumURL,
  ];
  const storefront =
    [...origin, ...appleURLs].find(
      (resource) => resource.service === "Apple Music"
    )?.storefront ?? "us";
  resources.push(...appleURLs);
  if (appleURLs.length || numericId.test(text(info.apple_music_id)))
    identities.push("Apple Music");
  if (!appleAlbumURL.length) {
    addDedicated(
      info.apple_album_id,
      "Apple Music",
      "album",
      numericId,
      `https://music.apple.com/${storefront}/album/`
    );
  }
  const songId = text(info.apple_music_id);
  const explicitAlbumId = text(info.apple_album_id);
  const appleAlbums = resources.filter(
    (resource) =>
      resource.service === "Apple Music" && resource.kind === "album"
  );
  const appleAlbum =
    appleAlbumURL[0] ??
    appleAlbums.find((album) => album.id === explicitAlbumId) ??
    (appleAlbums.length === 1 ? appleAlbums[0] : undefined);
  if (
    numericId.test(songId) &&
    appleAlbum &&
    !resources.some(
      (resource) =>
        resource.service === "Apple Music" &&
        resource.kind === "track" &&
        resource.id === songId
    )
  ) {
    resources.push({
      service: "Apple Music",
      kind: "track",
      id: songId,
      href: `${appleAlbum.href}?i=${songId}`,
      storefront,
    });
  }
  const unique = resources.filter(
    (resource, index) =>
      resources.findIndex(
        (other) =>
          other.service === resource.service &&
          other.kind === resource.kind &&
          other.id === resource.id &&
          other.storefront === resource.storefront
      ) === index
  );
  const links: MissingDataLink[] = [];
  const addLink = (
    kind: MissingDataLink["kind"],
    service: Service,
    label: string,
    href: string
  ) => {
    links.push({
      key: `${kind}:${service}:${href}`,
      kind,
      service,
      label,
      href,
    });
  };
  unique
    .filter((resource) => resource.kind !== "album")
    .forEach((resource) =>
      addLink(
        "source",
        resource.service,
        `Open in ${resource.service}`,
        resource.href
      )
    );
  const albums = unique.filter((resource) => resource.kind === "album");
  albums.forEach((album) =>
    addLink(
      "album",
      album.service,
      `Open album in ${album.service}`,
      album.href
    )
  );
  albums.forEach((album) => {
    const harmony = new URL("https://harmony.pulsewidth.org.uk/release");
    const sambl = new URL("https://sambl.lioncat6.com/seed");
    harmony.searchParams.set("url", album.href);
    sambl.searchParams.set("url", album.href);
    addLink(
      "harmony",
      album.service,
      `Look up album in Harmony (${album.service})`,
      harmony.href
    );
    addLink(
      "sambl",
      album.service,
      `Look up album in SAMBL (${album.service})`,
      sambl.href
    );
  });
  const source = sourceService(info, origin, identities);
  if (source && !albums.some((album) => album.service === source)) {
    const release = text(row.release_name);
    if (
      release ||
      !unique.some(
        (resource) => resource.service === source && resource.kind === "track"
      )
    ) {
      const query = [text(row.artist_name), release || text(row.recording_name)]
        .filter(Boolean)
        .join(" ")
        .replace(/\s+/g, " ");
      const href = query && searchURL(source, query, storefront);
      if (href)
        addLink(
          "search",
          source,
          `Search ${source} for ${release ? "album" : "track"}`,
          href
        );
    }
  }
  return links;
}
