/* eslint-disable camelcase */

export const MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION =
  "https://musicbrainz.org/doc/jspf#playlist";

export const MUSICBRAINZ_JSPF_TRACK_EXTENSION =
  "https://musicbrainz.org/doc/jspf#track";

export const PLAYLIST_URI_PREFIX = "https://listenbrainz.org/playlist/";
export const PLAYLIST_TRACK_URI_PREFIX = "https://musicbrainz.org/recording/";

export function getPlaylistExtension(
  playlist?: JSPFPlaylist
): {
  collaborators: string[];
  public: boolean;
  created_for?: string;
  copied_from?: string; // Full ListenBrainz playlist URI
  last_modified_at: string; // ISO date string
} | null {
  if (!playlist) {
    return null;
  }
  return playlist.extension?.[MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION] ?? null;
}

export function getPlaylistId(playlist?: JSPFPlaylist): string {
  return playlist?.identifier?.substr(PLAYLIST_URI_PREFIX.length) ?? "";
}

export function getRecordingMBIDFromJSPFTrack(track: JSPFTrack): string {
  return track.identifier?.[0].substr(PLAYLIST_TRACK_URI_PREFIX.length) ?? "";
}
