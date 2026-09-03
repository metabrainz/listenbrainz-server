import * as React from "react";
import { isFunction } from "lodash";
import { faGripLines } from "@fortawesome/free-solid-svg-icons";
import { faTrashCan } from "@fortawesome/free-regular-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import ListenCard from "../listens/ListenCard";
import ListenControl from "../listens/ListenControl";

type QueueItemCardProps = {
  track: BrainzPlayerQueueItem;
  removeTrackFromQueue?: (track: BrainzPlayerQueueItem) => void;
  hideDragHandle?: boolean;
};

function QueueItemCard(props: QueueItemCardProps) {
  const { track, removeTrackFromQueue, hideDragHandle = false } = props;

  const dragHandle = (
    <div className="drag-handle text-muted">
      <FontAwesomeIcon icon={faGripLines as IconProp} title="Drag to reorder" />
    </div>
  );

  let additionalAction;
  if (isFunction(removeTrackFromQueue)) {
    additionalAction = (
      <ListenControl
        title="Remove from Queue"
        buttonClassName="btn btn-transparent"
        text=""
        icon={faTrashCan}
        action={() => {
          removeTrackFromQueue(track);
        }}
      />
    );
  }

  return (
    <ListenCard
      className="queue-item-card"
      listen={track}
      showTimestamp={false}
      showUsername={false}
      beforeThumbnailContent={!hideDragHandle ? dragHandle : undefined}
      additionalActions={additionalAction}
    />
  );
}

export default React.memo(QueueItemCard);
