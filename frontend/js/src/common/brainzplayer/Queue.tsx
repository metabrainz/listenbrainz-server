import * as React from "react";
import { ReactSortable } from "react-sortablejs";
import NiceModal from "@ebay/nice-modal-react";
import { faChevronDown, faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import QueueItemCard from "./QueueItemCard";
import ListenCard from "../listens/ListenCard";
import CreateOrEditPlaylistModal from "../../playlists/components/CreateOrEditPlaylistModal";
import { listenToJSPFTrack } from "../../playlists/utils";
import { getListenCardKey } from "../../utils/utils";
import {
  useBrainzPlayerContext,
  useBrainzPlayerDispatch,
} from "./BrainzPlayerContext";

type BrainzPlayerQueueProps = {
  clearQueue: () => void;
  onHide: () => void;
};

const MAX_AMBIENT_QUEUE_ITEMS = 15;

function Queue(props: BrainzPlayerQueueProps) {
  const dispatch = useBrainzPlayerDispatch();
  const {
    queue,
    ambientQueue,
    currentListen,
    currentListenIndex = -1,
  } = useBrainzPlayerContext();

  const { clearQueue, onHide } = props;

  const removeTrackFromQueue = React.useCallback(
    (track: BrainzPlayerQueueItem, index: number) => {
      dispatch({
        type: "REMOVE_TRACK_FROM_QUEUE",
        data: {
          track,
          index,
        },
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const removeTrackFromAmbientQueue = React.useCallback(
    (track: BrainzPlayerQueueItem, index: number) => {
      dispatch({
        type: "REMOVE_TRACK_FROM_AMBIENT_QUEUE",
        data: {
          track,
          index,
        },
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const moveQueueItem = React.useCallback((evt: any) => {
    dispatch({
      type: "MOVE_QUEUE_ITEM",
      data: evt,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const moveAmbientQueueItemsToQueue = React.useCallback(() => {
    dispatch({
      type: "MOVE_AMBIENT_QUEUE_ITEMS_TO_QUEUE",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [queueNextUp, setQueueNextUp] = React.useState<BrainzPlayerQueue>([]);

  const addQueueToPlaylist = () => {
    const jspfTrackQueue = queue.map((track) => {
      return listenToJSPFTrack(track);
    });

    NiceModal.show(CreateOrEditPlaylistModal, {
      initialTracks: jspfTrackQueue,
    });
  };

  React.useEffect(() => {
    if (currentListen && currentListenIndex >= 0 && queue.length > 0) {
      if (currentListenIndex === queue.length - 1) {
        setQueueNextUp([]);
      } else {
        const nextUp = queue.slice(currentListenIndex + 1);
        setQueueNextUp(nextUp);
      }
    } else {
      // If there is no current listen track, show all tracks in the queue
      setQueueNextUp([...queue]);
    }
  }, [queue, currentListen, currentListenIndex]);

  return (
    <>
      <FontAwesomeIcon
        className="btn hide-queue"
        icon={faChevronDown}
        title="Hide queue"
        onClick={onHide}
      />
      {currentListen && (
        <>
          <div className="queue-headers">
            <h4>Now Playing:</h4>
            <div className="queue-buttons">
              <button
                className="btn btn-info btn-sm"
                data-toggle="modal"
                data-target="#CreateOrEditPlaylistModal"
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
          </div>
          <ListenCard
            key={`queue-listening-now-${getListenCardKey(currentListen)}}`}
            className="queue-item-card"
            listen={currentListen as Listen}
            showTimestamp={false}
            showUsername={false}
          />
        </>
      )}
      <div className="queue-headers">
        <h4>Next Up:</h4>
      </div>
      <div className="queue-list" data-testid="queue">
        {queueNextUp.length > 0 ? (
          <ReactSortable
            handle=".drag-handle"
            list={queueNextUp}
            onEnd={moveQueueItem}
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
                      removeTrackFromQueue(
                        trackToDelete,
                        index + currentListenIndex + 1
                      )
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
      <div className="queue-headers">
        <h4>On this page:</h4>
        {ambientQueue.length > 0 && (
          <div className="queue-buttons">
            <button
              className="btn btn-info btn-sm"
              onClick={moveAmbientQueueItemsToQueue}
              type="button"
            >
              Move to Queue
            </button>
          </div>
        )}
      </div>
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
                    ) => removeTrackFromAmbientQueue(trackToDelete, index)}
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
