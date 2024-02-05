import * as React from "react";
import { ReactSortable } from "react-sortablejs";
import NiceModal from "@ebay/nice-modal-react";
import { faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import QueueItemCard from "./QueueItemCard";
import ListenCard from "../listens/ListenCard";
import CreateOrEditPlaylistModal from "../../playlists/components/CreateOrEditPlaylistModal";
import { listenToJSPFTrack } from "../../playlists/utils";
import { getListenCardKey } from "../../utils/utils";

type QueueProps = {
  queue: BrainzPlayerQueue;
  ambientQueue: BrainzPlayerQueue;
  removeTrackFromQueue: (track: BrainzPlayerQueueItem) => void;
  moveQueueItem: (evt: any) => void;
  setQueue: (queue: BrainzPlayerQueue) => void;
  clearQueue: () => void;
  currentListen?: BrainzPlayerQueueItem;
};

function Queue(props: QueueProps) {
  const {
    queue,
    removeTrackFromQueue,
    setQueue,
    moveQueueItem,
    clearQueue,
    currentListen,
    ambientQueue,
  } = props;

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
    if (currentListen && queue.length > 0) {
      const currentListenIndex = queue.findIndex(
        (track) => track.id === currentListen.id
      );

      if (
        currentListenIndex === -1 ||
        currentListenIndex === queue.length - 1
      ) {
        setQueueNextUp([]);
      } else {
        const nextUp = queue.slice(currentListenIndex + 1);
        setQueueNextUp(nextUp);
      }
    } else {
      // If there is no current listen track, show all tracks in the queue
      setQueueNextUp([...queue]);
    }
  }, [queue, currentListen]);

  return (
    <>
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
      <div className="queue-list">
        {queueNextUp.length > 0 ? (
          <ReactSortable
            handle=".drag-handle"
            list={queueNextUp}
            onEnd={moveQueueItem}
            setList={() => {}}
          >
            {queueNextUp.map((queueItem: BrainzPlayerQueueItem) => {
              return (
                <QueueItemCard
                  key={queueItem.id}
                  track={queueItem}
                  removeTrackFromQueue={removeTrackFromQueue}
                />
              );
            })}
          </ReactSortable>
        ) : (
          <div className="lead text-center">
            <p>Nothing in this queue yet</p>
          </div>
        )}
      </div>
      <div className="queue-headers">
        <h4>On this page:</h4>
      </div>
      <div className="queue-list">
        {ambientQueue.length > 0
          ? ambientQueue.map((queueItem: BrainzPlayerQueueItem) => {
              return (
                <ListenCard
                  key={queueItem.id}
                  listen={queueItem as Listen}
                  showTimestamp={false}
                  showUsername={false}
                />
              );
            })
          : null}
      </div>
    </>
  );
}

export default React.memo(Queue);
