import * as React from "react";
import { get as _get } from "lodash";
import { faGripLines, faMinusCircle } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { JSPFTrackToListen } from "./utils";
import ListenCard from "../listens/ListenCard";
import ListenControl from "../listens/ListenControl";

export type PlaylistItemCardProps = {
  track: JSPFTrack;
  currentFeedback: ListenFeedBack;
  canEdit: Boolean;
  removeTrackFromPlaylist: (track: JSPFTrack) => void;
  updateFeedbackCallback: (
    recordingMsid: string,
    score: ListenFeedBack | RecommendationFeedBack,
    recordingMbid?: string
  ) => void;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

export default class PlaylistItemCard extends React.Component<
  PlaylistItemCardProps
> {
  removeTrack = () => {
    const { track, removeTrackFromPlaylist } = this.props;
    removeTrackFromPlaylist(track);
  };

  render() {
    const {
      track,
      canEdit,
      currentFeedback,
      newAlert,
      updateFeedbackCallback,
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
    if (canEdit) {
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
        currentFeedback={currentFeedback}
        showTimestamp={Boolean(listen.listened_at_iso)}
        showUsername={Boolean(listen.user_name)}
        // showTrackLength
        newAlert={newAlert}
        beforeThumbnailContent={dragHandle}
        data-recording-mbid={track.id}
        additionalMenuItems={additionalMenuItems}
        updateFeedbackCallback={updateFeedbackCallback}
      />
    );
  }
}
