/* eslint-disable camelcase */

import { padStart } from "lodash";

export const MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION =
  "https://musicbrainz.org/doc/jspf#playlist";

export const MUSICBRAINZ_JSPF_TRACK_EXTENSION =
  "https://musicbrainz.org/doc/jspf#track";

export const PLAYLIST_URI_PREFIX = "https://listenbrainz.org/playlist/";
export const PLAYLIST_TRACK_URI_PREFIX = "https://musicbrainz.org/recording/";

export function getPlaylistExtension(
  playlist?: JSPFPlaylist
): JSPFPlaylistExtension | null {
  if (!playlist) {
    return null;
  }
  return playlist.extension?.[MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION] ?? null;
}

export function getTrackExtension(
  track?: JSPFTrack
): JSPFTrackExtension | null {
  if (!track) {
    return null;
  }
  return track.extension?.[MUSICBRAINZ_JSPF_TRACK_EXTENSION] ?? null;
}

export function getPlaylistId(playlist?: JSPFPlaylist): string {
  return playlist?.identifier?.substr(PLAYLIST_URI_PREFIX.length) ?? "";
}

export function getRecordingMBIDFromJSPFTrack(track: JSPFTrack): string {
  return track.identifier?.substr(PLAYLIST_TRACK_URI_PREFIX.length) ?? "";
}

// Credit goes to Dmitry Sheiko https://stackoverflow.com/a/53006402/4904467
export function millisecondsToStr(milliseconds: number) {
  let temp = milliseconds / 1000;
  const days = Math.floor((temp %= 31536000) / 86400);
  const hours = Math.floor((temp %= 86400) / 3600);
  const minutes = Math.floor((temp %= 3600) / 60);
  const seconds = temp % 60;

  if (seconds > 1 && !minutes && !hours) {
    return `${seconds.toFixed(0)}s`;
  }
  if (hours || minutes) {
    return `${
      (days ? `${days}d ` : "") +
      (hours ? `${hours}:` : "") +
      (minutes ? `${minutes}:` : "") +
      padStart(seconds.toFixed(0), 2, "0")
    }`;
  }

  return "< 1s";
}
