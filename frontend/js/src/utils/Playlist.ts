import APIService from "./APIService";
import {
  JSPFTrackToListen,
  MUSICBRAINZ_JSPF_TRACK_EXTENSION,
  getRecordingMBIDFromJSPFTrack,
} from "../playlists/utils";

export default async function enrichJSPFTracks(
  tracks: JSPFObject["playlist"]["track"],
  api: APIService
): Promise<
  (JSPFObject["playlist"]["track"][number] & {
    duration?: number;
    extension?: {
      [key: string]: {
        additional_metadata: {
          caa_id?: number;
          caa_release_mbid?: string;
          artists?: {
            artist_credit_name: string;
            artist_mbid: string;
            join_phrase: string;
          }[];
        };
      };
    };
  })[]
> {
  const mbids = tracks.map(getRecordingMBIDFromJSPFTrack);
  const metadataMap = await api.getRecordingMetadata(mbids);
  if (!metadataMap) {
    throw new Error("Failed to fetch metadata map");
  }
  return tracks.map((track) => {
    const mbid = getRecordingMBIDFromJSPFTrack(track);
    const meta = metadataMap[mbid];
    if (!meta) return track;
    return {
      ...track,
      duration: meta.recording?.length,
      extension: {
        [MUSICBRAINZ_JSPF_TRACK_EXTENSION]: {
          additional_metadata: {
            caa_id: meta.release?.caa_id,
            caa_release_mbid: meta.release?.caa_release_mbid,
            artists: meta.artist?.artists?.map((a) => ({
              artist_credit_name: a.name,
              artist_mbid: a.artist_mbid,
              join_phrase: a.join_phrase || "",
            })),
          },
          added_by:
            track.extension?.[MUSICBRAINZ_JSPF_TRACK_EXTENSION]?.added_by || "",
          added_at:
            track.extension?.[MUSICBRAINZ_JSPF_TRACK_EXTENSION]?.added_at || "",
        },
      },
    };
  });
}
