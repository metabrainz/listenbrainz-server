import { cloneDeep, has } from "lodash";
import { v4 as uuidv4 } from "uuid";
import { JSPFTrackToListen } from "../../playlists/utils";
import { getListenCardKey } from "../../utils/utils";

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
    id: `queue-item-${getListenCardKey(
      listenTrack
    )}-${Date.now().toString()}-${uuidv4()}`,
  };
  return queueItem;
}
