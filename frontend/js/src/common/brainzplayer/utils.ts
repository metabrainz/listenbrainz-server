import { cloneDeep, has } from "lodash";
import { JSPFTrackToListen } from "../../playlists/utils";
import {
  getArtistMBIDs,
  getArtistName,
  getRecordingMBID,
  getRecordingMSID,
  getReleaseGroupMBID,
  getReleaseMBID,
  getReleaseName,
  getTrackName,
} from "../../utils/utils";
import SpotifyPlayer from "./SpotifyPlayer";
import YoutubePlayer from "./YoutubePlayer";
import AppleMusicPlayer from "./AppleMusicPlayer";

const getBrainzPlayerQueueItemKey = (listen: Listen): string =>
  `${getRecordingMSID(listen)}-${getTrackName(listen)}-${getArtistName(
    listen
  )}-${getReleaseName(listen)}-${
    listen.track_metadata?.mbid_mapping?.release_group_name
  }-${getRecordingMBID(listen)}-${getArtistMBIDs(listen)?.join(
    ","
  )}-${getReleaseMBID(listen)}-${getReleaseGroupMBID(listen)}-${
    listen.track_metadata?.mbid_mapping?.caa_id
  }-${listen.track_metadata?.mbid_mapping?.caa_release_mbid}-${
    listen.listened_at
  }-${listen.inserted_at}`;

const getMatchedTrack = (listen: Listen): MatchedTrack => {
  const spotifyURI = SpotifyPlayer.getSpotifyUriFromListen(listen);
  const youtubeURI = YoutubePlayer.getVideoIDFromListen(listen);
  const appleMusicURI = AppleMusicPlayer.getURLFromListen(listen);
  return {
    spotify: spotifyURI ?? undefined,
    youtube: youtubeURI ?? undefined,
    appleMusic: appleMusicURI ?? undefined,
  };
};

// eslint-disable-next-line import/prefer-default-export
export function listenOrJSPFTrackToQueueItem(
  track: Listen | JSPFTrack
): BrainzPlayerQueueItem {
  let listenTrack: Listen;
  if (has(track, "title")) {
    listenTrack = JSPFTrackToListen(track as JSPFTrack);
  } else {
    listenTrack = cloneDeep(track as BrainzPlayerQueueItem);
  }
  const matchedTrack = getMatchedTrack(listenTrack);
  const queueItem = {
    ...listenTrack,
    id: `queue-item-${getBrainzPlayerQueueItemKey(listenTrack)}`,
    matchedTrack,
  };
  return queueItem;
}
