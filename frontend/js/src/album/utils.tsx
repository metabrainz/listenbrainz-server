import * as React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import {
  faBarcode,
  faCircleNodes,
  faCompactDisc,
  faHomeAlt,
  faLink,
  faMicrophone,
  faMusic,
} from "@fortawesome/free-solid-svg-icons";
import {
  faAmazon,
  faApple,
  faBandcamp,
  faDeezer,
  faFacebook,
  faInstagram,
  faLastfm,
  faSoundcloud,
  faSpotify,
  faTidal,
  faTwitter,
} from "@fortawesome/free-brands-svg-icons";
import { dataSourcesInfo } from "../settings/brainzplayer/BrainzPlayerSettings";
import { faQobuz } from "../common/icons/faQobuz";

export type SimilarArtist = {
  artist_mbid: string;
  comment: string;
  gender: string | null;
  name: string;
  reference_mbid: string;
  score: number;
  type: "Group" | "Person";
};

export type ReleaseGroup = {
  caa_id: number;
  caa_release_mbid: string;
  date: string | null;
  mbid: string;
  name: string;
  type: string;
  artists: Array<MBIDMappingArtist>;
};

export type PopularRecording = {
  artist_mbids: string[];
  artist_name: string;
  artists?: Array<MBIDMappingArtist>;
  caa_id?: number;
  caa_release_mbid?: string;
  position?: number;
  length: number;
  recording_mbid: string;
  recording_name: string;
  release_mbid: string;
  release_name: string;
  total_listen_count: number;
  total_user_count: number;
};

export type ListeningStats = {
  total_listen_count?: number;
  total_user_count?: number;
  listeners: Array<{
    user_name: string;
    listen_count: number;
  }>;
};

/** Streaming services recognised by hostname, for links MusicBrainz only
 * describes as "streaming" or "free streaming".
 *
 * `icon` is optional in case there is no Font Awesome brand icon.
 */
const streamingServices: Array<{
  pattern: RegExp;
  name: string;
  icon?: IconDefinition;
  color?: string;
}> = [
  {
    pattern: /(^|\.)qobuz\.com$/,
    name: "Qobuz",
    icon: faQobuz,
    color: "#0070EF",
  },
  {
    pattern: /(^|\.)tidal\.com$/,
    name: "Tidal",
    icon: faTidal,
  },
  {
    pattern: /(^|\.)deezer\.com$/,
    name: "Deezer",
    icon: faDeezer,
    color: "#A238FF",
  },
  {
    pattern: /(^|\.)spotify\.com$/,
    name: "Spotify",
    icon: faSpotify,
    color: dataSourcesInfo.spotify.color,
  },
  {
    // The TLD is anchored so that a subdomain of someone else's domain --
    // amazon.evil.com -- cannot match, while the real regional TLDs do.
    pattern: /(^|\.)(music\.)?amazon\.(com|[a-z]{2,3}(\.[a-z]{2})?)$/,
    name: "Amazon Music",
    icon: faAmazon,
    color: "#FF9900",
  },
  {
    pattern: /(^|\.)music\.apple\.com$/,
    name: "Apple Music",
    icon: faApple,
    color: dataSourcesInfo.appleMusic.color,
  },
  {
    pattern: /(^|\.)bandcamp\.com$/,
    name: "Bandcamp",
    icon: faBandcamp,
    color: "#629AA9",
  },
  {
    pattern: /(^|\.)soundcloud\.com$/,
    name: "SoundCloud",
    icon: faSoundcloud,
    color: dataSourcesInfo.soundcloud.color,
  },
  { pattern: /(^|\.)jiosaavn\.com$/, name: "JioSaavn" },
  { pattern: /(^|\.)gaana\.com$/, name: "Gaana" },
  { pattern: /(^|\.)audiomack\.com$/, name: "Audiomack" },
  { pattern: /(^|\.)napster\.com$/, name: "Napster" },
  { pattern: /(^|\.)pandora\.com$/, name: "Pandora" },
  { pattern: /(^|\.)music\.yandex\.[a-z]+$/, name: "Yandex Music" },
  { pattern: /(^|\.)boomplay\.com$/, name: "Boomplay" },
  { pattern: /(^|\.)anghami\.com$/, name: "Anghami" },
];

/** Identify the streaming service a URL points at, by hostname.
 *
 * Matching on the hostname rather than the whole URL keeps a service name in a
 * path or query string (".../artist/tidal-tribute") from being mistaken for the
 * host. Returns undefined for anything unrecognised, and for a URL that does
 * not parse, so callers fall back to the relationship name.
 */
export function getStreamingServiceFromURL(url: string) {
  let hostname;
  try {
    ({ hostname } = new URL(url));
  } catch {
    return undefined;
  }
  return streamingServices.find(({ pattern }) => pattern.test(hostname));
}

function YouTubeLogo() {
  return (
    <svg
      aria-hidden="true"
      className="youtube-brand-icon"
      focusable="false"
      viewBox="0 0 28 20"
    >
      <path
        d="M27.4 3.1a3.5 3.5 0 0 0-2.5-2.5C22.7 0 14 0 14 0S5.3 0 3.1.6A3.5 3.5 0 0 0 .6 3.1C0 5.3 0 10 0 10s0 4.7.6 6.9a3.5 3.5 0 0 0 2.5 2.5C5.3 20 14 20 14 20s8.7 0 10.9-.6a3.5 3.5 0 0 0 2.5-2.5C28 14.7 28 10 28 10s0-4.7-.6-6.9Z"
        fill="#f00"
      />
      <path
        d="m11.2 14.3 7.2-4.3-7.2-4.3v8.6Z"
        data-testid="youtube-brand-play"
        fill="#fff"
      />
    </svg>
  );
}

export function getRelIconLink(relName: string, relValue: string) {
  let icon;
  let color;
  let isYoutube = false;
  let isTidal = false;
  // Falls back to the relationship name, which is all we had before.
  let title = relName;
  switch (relName) {
    case "streaming":
    case "free streaming": {
      const service = getStreamingServiceFromURL(relValue);
      icon = service?.icon ?? faMusic;
      color = service?.color;
      title = service?.name ?? relName;
      isTidal = service?.name === "Tidal";
      break;
    }
    case "lyrics":
      icon = faMicrophone;
      break;
    case "wikidata":
      icon = faBarcode;
      break;
    case "youtube":
    case "youtube music":
      color = dataSourcesInfo.youtube.color;
      isYoutube = true;
      break;
    case "soundcloud":
      icon = faSoundcloud;
      color = dataSourcesInfo.soundcloud.color;
      break;
    case "official homepage":
      icon = faHomeAlt;
      break;
    case "bandcamp":
      icon = faBandcamp;
      color = "#629AA9";
      break;
    case "last.fm":
      icon = faLastfm;
      color = "#D51007";
      break;
    case "apple music":
      icon = faApple;
      color = dataSourcesInfo.appleMusic.color;
      break;
    case "get the music":
    case "purchase for mail-order":
    case "purchase for download":
    case "download for free":
      icon = faCompactDisc;
      break;
    case "social network":
    case "online community":
      if (/instagram/.test(relValue)) {
        icon = faInstagram;
      } else if (/facebook/.test(relValue)) {
        icon = faFacebook;
      } else if (/twitter/.test(relValue) || /x.com/.test(relValue)) {
        icon = faTwitter;
        color = "#55ACEE";
      } else if (/soundcloud/.test(relValue)) {
        icon = faSoundcloud;
        color = dataSourcesInfo.soundcloud.color;
      } else {
        icon = faCircleNodes;
      }
      break;
    default:
      icon = faLink;
      break;
  }
  return (
    <a
      key={relName}
      href={relValue}
      title={title}
      className={`btn btn-icon btn-link${isTidal ? " brand-tidal" : ""}`}
      target="_blank"
      rel="noopener noreferrer"
    >
      {isYoutube ? (
        <YouTubeLogo />
      ) : (
        <FontAwesomeIcon icon={icon ?? faMusic} fixedWidth color={color} />
      )}
    </a>
  );
}

export function noop() {}

export function popularRecordingToListen(recording: PopularRecording): Listen {
  return {
    listened_at: 0,
    track_metadata: {
      artist_name: recording.artist_name,
      track_name: recording.recording_name,
      release_name: recording.release_name,
      additional_info: {
        artist_mbids: recording.artist_mbids,
        recording_mbid: recording.recording_mbid,
        duration_ms: recording.length,
        release_mbid: recording.release_mbid,
        tracknumber: recording.position ?? null,
      },
      mbid_mapping: {
        caa_id: recording.caa_id,
        caa_release_mbid: recording.caa_release_mbid,
        recording_mbid: recording.recording_mbid,
        release_mbid: recording.release_mbid,
        artist_mbids: recording.artist_mbids,
        artists: recording.artists,
      },
    },
  };
}
