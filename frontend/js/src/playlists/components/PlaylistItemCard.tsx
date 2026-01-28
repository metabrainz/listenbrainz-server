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
    if (canEdit && isFunction(removeTrackFromPlaylist)) {
      additionalMenuItems = [
        <ListenControl
          title="Remove from playlist"
          text="Remove from playlist"
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
