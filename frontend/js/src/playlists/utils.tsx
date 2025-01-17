import { getArtistName, getRecordingMBID, getTrackName } from "../utils/utils";

export const MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION =
  "https://musicbrainz.org/doc/jspf#playlist";

export const MUSICBRAINZ_JSPF_TRACK_EXTENSION =
  "https://musicbrainz.org/doc/jspf#track";

export const LISTENBRAINZ_URI_PREFIX = "https://listenbrainz.org/";
export const PLAYLIST_URI_PREFIX = `${LISTENBRAINZ_URI_PREFIX}playlist/`;
export const PLAYLIST_TRACK_URI_PREFIX = "https://musicbrainz.org/recording/";
export const PLAYLIST_ARTIST_URI_PREFIX = "https://musicbrainz.org/artist/";

export enum PlaylistType {
  "playlists",
  "collaborations",
  "recommendations",
}

export function isPlaylistOwner(
  playlist: JSPFPlaylist,
  user: ListenBrainzUser
): boolean {
  return Boolean(user) && user?.name === playlist.creator;
}

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
  return playlist?.identifier?.replace(PLAYLIST_URI_PREFIX, "") ?? "";
}

export function getRecordingMBIDFromJSPFTrack(track: JSPFTrack): string {
  const { identifier } = track;
  let identifiers: string[];
  if (typeof identifier === "string") {
    identifiers = [identifier];
  } else {
    identifiers = identifier;
  }
  return (
    identifiers
      ?.find((iden) => iden.startsWith(PLAYLIST_TRACK_URI_PREFIX))
      ?.replace(PLAYLIST_TRACK_URI_PREFIX, "") ?? ""
  );
}
export function getArtistMBIDFromURI(URI: string): string {
  return URI?.replace(PLAYLIST_ARTIST_URI_PREFIX, "") ?? "";
}

// Originally by Sinjai https://stackoverflow.com/a/67462589
export function millisecondsToStr(milliseconds: number) {
  function pad(num: number) {
    return `${num}`.padStart(2, "0");
  }
  const asSeconds = milliseconds / 1000;

  let hours;
  let minutes = Math.floor(asSeconds / 60);
  const seconds = Math.floor(asSeconds % 60);

  if (minutes > 59) {
    hours = Math.floor(minutes / 60);
    minutes %= 60;
  }

  return hours
    ? `${hours}:${pad(minutes)}:${pad(seconds)}`
    : `${minutes}:${pad(seconds)}`;
}

export function JSPFTrackToListen(track: JSPFTrack): Listen {
  const customFields = getTrackExtension(track);
  const recordingMBID = getRecordingMBIDFromJSPFTrack(track);
  const listen: Listen = {
    listened_at: 0,
    track_metadata: {
      artist_name: track.creator,
      track_name: track.title,
      release_name: track.album,
      additional_info: {
        duration_ms: track.duration,
        recording_mbid: recordingMBID,
        origin_url: track.location?.[0],
      },
    },
    user_name: customFields?.added_by,
  };
  const caa_id = customFields?.additional_metadata?.caa_id;
  const caa_release_mbid = customFields?.additional_metadata?.caa_release_mbid;

  listen.track_metadata.mbid_mapping = {
    artist_mbids:
      customFields?.artist_identifiers?.map(getArtistMBIDFromURI) ?? [],
    artists: customFields?.additional_metadata?.artists ?? [],
    recording_mbid: recordingMBID,
    release_mbid: caa_release_mbid,
    caa_id,
    caa_release_mbid,
  };

  if (customFields?.added_at) {
    listen.listened_at_iso = customFields.added_at;
  }
  if (listen.track_metadata?.additional_info) {
    listen.track_metadata.additional_info.artist_mbids = customFields?.artist_identifiers?.map(
      getArtistMBIDFromURI
    );
  }
  return listen;
}

export function listenToJSPFTrack(listen: Listen): JSPFTrack {
  const recordingMBID = getRecordingMBID(listen);
  const trackName = getTrackName(listen);
  const artistName = getArtistName(listen);
  return {
    identifier: PLAYLIST_TRACK_URI_PREFIX + recordingMBID,
    id: recordingMBID || undefined,
    title: trackName,
    creator: artistName,
    album: listen.track_metadata?.release_name || undefined,
    duration: listen.track_metadata?.additional_info?.duration_ms || undefined,
    location: listen.track_metadata?.additional_info?.origin_url
      ? [listen.track_metadata?.additional_info?.origin_url]
      : undefined,
  };
}
