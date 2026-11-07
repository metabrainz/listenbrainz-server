import * as React from "react";
import { get as _get, isFunction, isUndefined } from "lodash";
import { faGripLines, faMinusCircle } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { JSPFTrackToListen } from "../utils";
import ListenCard from "../../common/listens/ListenCard";
import ListenControl from "../../common/listens/ListenControl";

export type PlaylistItemCardProps = {
  track: JSPFTrack;
  canEdit: Boolean;
  // Allows removing a track without enabling the rest of the edit UI (drag to reorder).
  // Defaults to the value of canEdit.
  canRemove?: Boolean;
  removeTrackText?: string;
  removeTrackFromPlaylist?: (track: JSPFTrack) => void;
  showTimestamp?: boolean;
  showUsername?: boolean;
};

export default class PlaylistItemCard extends React.Component<
  PlaylistItemCardProps
> {
  removeTrack = () => {
    const { track, removeTrackFromPlaylist } = this.props;
    if (removeTrackFromPlaylist) {
      removeTrackFromPlaylist(track);
    }
  };

  render() {
    const {
      track,
      canEdit,
      canRemove = canEdit,
      removeTrackText = "Remove from playlist",
      showUsername,
      showTimestamp,
      removeTrackFromPlaylist,
    } = this.props;
    // const customFields = getTrackExtension(track);
    // const trackDuration = track.duration
    //   ? millisecondsToStr(track.duration)
    //   : null;

    const dragHandle = canEdit ? (
      <div className="drag-handle text-muted">
        <FontAwesomeIcon
          icon={faGripLines as IconProp}
          title="Drag to reorder"
        />
      </div>
    ) : undefined;
    let additionalMenuItems;
    if (canRemove && isFunction(removeTrackFromPlaylist)) {
      additionalMenuItems = [
        <ListenControl
          title={removeTrackText}
          text={removeTrackText}
          icon={faMinusCircle}
          action={this.removeTrack}
        />,
      ];
    }
    const listen = JSPFTrackToListen(track);
    return (
      <ListenCard
        className="playlist-item-card"
        listen={listen}
        showTimestamp={showTimestamp ?? Boolean(listen.listened_at_iso)}
        showUsername={showUsername ?? Boolean(listen.user_name)}
        beforeThumbnailContent={dragHandle}
        data-recording-mbid={track.id}
        additionalMenuItems={additionalMenuItems}
      />
    );
  }
}
