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
  const queueItem = {
    ...listenTrack,
    id: `queue-item-${getBrainzPlayerQueueItemKey(listenTrack)}`,
  };
  return queueItem;
}

export enum FeedbackValue {
  LIKE = 1,
  DISLIKE = -1,
  NEUTRAL = 0,
}
