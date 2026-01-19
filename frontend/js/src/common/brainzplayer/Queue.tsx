import * as React from "react";
import { ReactSortable } from "react-sortablejs";
import NiceModal from "@ebay/nice-modal-react";
import { faChevronDown, faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useAtomValue, useSetAtom } from "jotai";
import humanizeDuration from "humanize-duration";
import QueueItemCard from "./QueueItemCard";
import ListenCard from "../listens/ListenCard";
import CreateOrEditPlaylistModal from "../../playlists/components/CreateOrEditPlaylistModal";
import { listenToJSPFTrack } from "../../playlists/utils";
import { getListenCardKey, getTrackDurationInMs } from "../../utils/utils";
import {
  queueAtom,
  ambientQueueAtom,
  currentListenAtom,
  moveAmbientQueueItemsToQueueAtom,
  removeTrackFromAmbientQueueAtom,
  moveQueueItemAtom,
  removeTrackFromQueueAtom,
  currentListenIndexAtom,
  progressMsAtom,
  durationMsAtom,
} from "./BrainzPlayerAtoms";

const shortEnglishHumanizer = humanizeDuration.humanizer({
  language: "shortEn",
  languages: {
    shortEn: {
      y: () => "y",
      mo: () => "mo",
      w: () => "w",
      d: () => "d",
      h: () => "h",
      m: () => "m",
      s: () => "s",
      ms: () => "ms",
    },
  },
});

type BrainzPlayerQueueProps = {
  clearQueue: () => void;
  onHide: () => void;
};

const MAX_AMBIENT_QUEUE_ITEMS = 15;

function Queue(props: BrainzPlayerQueueProps) {
  const currentListen = useAtomValue(currentListenAtom);
  const ambientQueue = useAtomValue(ambientQueueAtom);
  const queue = useAtomValue(queueAtom);

  const progressMs = useAtomValue(progressMsAtom);
  const durationMs = useAtomValue(durationMsAtom);

  const moveAmbientQueueItemsToQueue = useSetAtom(
    moveAmbientQueueItemsToQueueAtom
  );
  const removeTrackFromAmbientQueue = useSetAtom(
    removeTrackFromAmbientQueueAtom
  );
  const moveQueueItem = useSetAtom(moveQueueItemAtom);
  const removeTrackFromQueue = useSetAtom(removeTrackFromQueueAtom);

  const currentListenIndex = useAtomValue(currentListenIndexAtom);

  const { clearQueue, onHide } = props;

  const [queueNextUp, setQueueNextUp] = React.useState<BrainzPlayerQueue>([]);

  React.useEffect(() => {
    if (currentListen && currentListenIndex >= 0 && queue.length > 0) {
      if (currentListenIndex === queue.length - 1) {
        setQueueNextUp([]);
      } else {
        const nextUp = queue.slice(currentListenIndex + 1);
        setQueueNextUp(nextUp);
      }
    } else {
      setQueueNextUp([...queue]);
    }
  }, [queue, currentListen, currentListenIndex]);
  const queueDurationMs = React.useMemo(() => {
    let total = 0;
    queueNextUp.forEach((track) => {
      total += Number(getTrackDurationInMs(track)) || 0;
    });
    return total;
  }, [queueNextUp]);

  const totalRemainingTime = React.useMemo(() => {
    let totalMs = queueDurationMs;

    if (currentListen) {
      const currentTrackDuration =
        Number(getTrackDurationInMs(currentListen)) || durationMs;

      const remaining = Math.max(0, currentTrackDuration - progressMs);
      totalMs += remaining;
    }

    if (totalMs <= 0) return "0s";
    const isOverTenMinutes = totalMs >= 600000;

    return shortEnglishHumanizer(totalMs, {
      round: true,
      units: isOverTenMinutes ? ["h", "m"] : ["h", "m", "s"],
      delimiter: " ",
      spacer: "",
    });
  }, [queueDurationMs, currentListen, progressMs, durationMs]);

  const addQueueToPlaylist = () => {
    const jspfTrackQueue = queue.map((track) => {
      return listenToJSPFTrack(track);
    });

    NiceModal.show(CreateOrEditPlaylistModal, {
      initialTracks: jspfTrackQueue,
    });
  };

  return (
    <>
      <FontAwesomeIcon
        className="btn hide-queue"
        icon={faChevronDown}
        title="Hide queue"
        onClick={onHide}
      />
      {queueNextUp.length > 0 && (
        <div className="queue-buttons d-flex justify-content-end gap-3">
          <button
            className="btn btn-info btn-sm"
            onClick={addQueueToPlaylist}
            type="button"
          >
            <FontAwesomeIcon icon={faSave} fixedWidth /> Save to Playlist
          </button>
          <button
            className="btn btn-info btn-sm"
            onClick={clearQueue}
            type="button"
          >
            Clear Queue
          </button>
        </div>
      )}
      {currentListen && (
        <>
          <div className="queue-headers">
            <h4>Now Playing:</h4>
          </div>
          <ListenCard
            key={`queue-listening-now-${getListenCardKey(currentListen)}`}
            className="queue-item-card"
            listen={currentListen as Listen}
            showTimestamp={false}
            showUsername={false}
          />
        </>
      )}

      {currentListen ? (
        <div className="queue-headers d-flex justify-content-between align-items-center">
          <h4>Next Up:</h4>
          {queueNextUp.length > 0 && (
            <span className="text-secondary" style={{ fontSize: "1.2rem" }}>
              {queueNextUp.length}{" "}
              {queueNextUp.length === 1 ? "track" : "tracks"} -{" "}
              {totalRemainingTime} left
            </span>
          )}
        </div>
      ) : (
        <div className="queue-headers d-flex align-items-center gap-3">
          <h4 className="m-0">Next Up:</h4>
          {queueNextUp.length > 0 && (
            <span className="text-secondary" style={{ fontSize: "1.2rem" }}>
              {queueNextUp.length}{" "}
              {queueNextUp.length === 1 ? "track" : "tracks"} -{" "}
              {totalRemainingTime} left
            </span>
          )}
        </div>
      )}

      <div className="queue-list" data-testid="queue">
        {queueNextUp.length > 0 ? (
          <ReactSortable
            handle=".drag-handle"
            list={queueNextUp}
            onEnd={(evt) =>
              moveQueueItem({
                oldIndex: evt.oldIndex ?? 0,
                newIndex: evt.newIndex ?? 0,
              })
            }
            setList={() => {}}
          >
            {queueNextUp.map(
              (queueItem: BrainzPlayerQueueItem, index: number) => {
                if (!queueItem) return null;
                return (
                  <QueueItemCard
                    key={`${queueItem?.id}-${index.toString()}`}
                    track={queueItem}
                    removeTrackFromQueue={(
                      trackToDelete: BrainzPlayerQueueItem
                    ) =>
                      removeTrackFromQueue({
                        track: trackToDelete,
                        index: index + currentListenIndex + 1,
                      })
                    }
                  />
                );
              }
            )}
          </ReactSortable>
        ) : (
          <div className="lead text-center">
            <p>Nothing in this queue yet</p>
          </div>
        )}
      </div>
      {ambientQueue.length > 0 && (
        <>
          <div className="queue-buttons">
            <button
              className="btn btn-info btn-sm"
              onClick={moveAmbientQueueItemsToQueue}
              type="button"
            >
              Move to Queue
            </button>
          </div>
          <div className="queue-headers">
            <h4>On this page:</h4>
          </div>
        </>
      )}
      <div className="queue-list" data-testid="ambient-queue">
        {ambientQueue.length > 0
          ? ambientQueue
              .slice(0, MAX_AMBIENT_QUEUE_ITEMS)
              .map((queueItem: BrainzPlayerQueueItem, index: number) => {
                if (!queueItem) return null;
                return (
                  <QueueItemCard
                    key={queueItem?.id}
                    track={queueItem}
                    removeTrackFromQueue={(
                      trackToDelete: BrainzPlayerQueueItem
                    ) =>
                      removeTrackFromAmbientQueue({
                        track: trackToDelete,
                        index,
                      })
                    }
                    hideDragHandle
                  />
                );
              })
          : null}
      </div>
    </>
  );
}

export default React.memo(Queue);
