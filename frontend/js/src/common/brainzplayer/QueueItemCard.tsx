import * as React from "react";
import { isFunction } from "lodash";
import { faGripLines, faTrash } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import ListenCard from "../listens/ListenCard";
import ListenControl from "../listens/ListenControl";

type QueueItemCardProps = {
  track: BrainzPlayerQueueItem;
  removeTrackFromQueue?: (track: BrainzPlayerQueueItem) => void;
};

function QueueItemCard(props: QueueItemCardProps) {
  const { track, removeTrackFromQueue } = props;

  const removeTrack = () => {
    if (removeTrackFromQueue) {
      removeTrackFromQueue(track);
    }
  };

  const dragHandle = (
    <div className="drag-handle text-muted">
      <FontAwesomeIcon icon={faGripLines as IconProp} title="Drag to reorder" />
    </div>
  );

  let additionalMenuItems;
  if (isFunction(removeTrackFromQueue)) {
    additionalMenuItems = [
      <ListenControl
        title="Remove from Queue"
        text="Remove from Queue"
        icon={faTrash}
        action={removeTrack}
      />,
    ];
  }

  return (
    <ListenCard
      className="queue-item-card"
      listen={track}
      showTimestamp={false}
      showUsername={false}
      beforeThumbnailContent={dragHandle}
      additionalMenuItems={additionalMenuItems}
    />
  );
}

export default React.memo(QueueItemCard);
