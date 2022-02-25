import * as React from "react";
import {
  faCog,
  faFastBackward,
  faFastForward,
  faHeart,
  faHeartBroken,
  faPauseCircle,
  faPlayCircle,
} from "@fortawesome/free-solid-svg-icons";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { get, isNaN as _isNaN } from "lodash";
import ProgressBar from "./ProgressBar";
import GlobalAppContext from "../utils/GlobalAppContext";
import MenuOptions from "./MenuOptions";

type BrainzPlayerUIProps = {
  playPreviousTrack: () => void;
  playNextTrack: (invert?: boolean) => void;
  togglePlay: (invert?: boolean) => void;
  playerPaused: boolean;
  trackName?: string;
  artistName?: string;
  progressMs: number;
  durationMs: number;
  seekToPositionMs: (msTimeCode: number) => void;
  currentListen?: Listen | JSPFTrack;
  listenBrainzAPIBaseURI: string;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

type PlaybackControlButtonProps = {
  className: string;
  action: () => void;
  icon: IconDefinition;
  title: string;
  size?: "2x";
};

const PlaybackControlButton = (props: PlaybackControlButtonProps) => {
  const { className, action, icon, title, size } = props;
  return (
    <div
      className={className}
      title={title}
      onClick={action}
      onKeyPress={action}
      role="button"
      tabIndex={0}
    >
      <FontAwesomeIcon icon={icon as IconProp} size={size} />
    </div>
  );
};

const BrainzPlayerUI = (
  props: React.PropsWithChildren<BrainzPlayerUIProps>
) => {
  const { listenBrainzAPIBaseURI, currentListen, newAlert } = props;
  const [currentListenFeedback, setCurrentListenFeedback] = React.useState(0);
  const { currentUser } = React.useContext(GlobalAppContext);
  // const { currentListenFeedback } = this.state;
  React.useEffect(() => {
    async function getFeedback() {
      // Get feedback for currentListen

      if (!currentUser?.name) {
        return;
      }
      const recordingMBID = get(
        currentListen,
        "track_metadata.additional_info.recording_mbid"
      );
      const recordingMSID = get(
        currentListen,
        "track_metadata.additional_info.recording_msid"
      );
      if (!recordingMBID && !recordingMSID) {
        return;
      }
      try {
        const baseURL = `${listenBrainzAPIBaseURI}/feedback/user/${currentUser.name}/get-feedback-for-recordings?`;
        // get feedback by either MBID or MSID
        const params = [];
        if (recordingMBID) {
          params.push(`recording_mbids=${recordingMBID}`);
        }
        if (recordingMSID) {
          params.push(`recording_msids=${recordingMSID}`);
        }

        const response = await fetch(`${baseURL}${params.join("&")}`);
        if (!response.ok) {
          throw response.statusText;
        }
        const parsedFeedback = await response.json();
        setCurrentListenFeedback(parsedFeedback.feedback?.[0]?.score ?? 0);
      } catch (error) {
        // What do we do here?
        // Is there any point in showing an error message?
      }
    }
    getFeedback();
  }, [currentListen]);

  async function submitFeedback(score: ListenFeedBack) {
    if (currentUser?.auth_token) {
      setCurrentListenFeedback(score);
      const recordingMSID = get(
        currentListen,
        "track_metadata.additional_info.recording_msid"
      );
      const recordingMBID = get(
        currentListen,
        "track_metadata.additional_info.recording_mbid"
      );

      try {
        const url = `${listenBrainzAPIBaseURI}/feedback/recording-feedback`;
        const response = await fetch(url, {
          method: "POST",
          headers: {
            Authorization: `Token ${currentUser.auth_token}`,
            "Content-Type": "application/json;charset=UTF-8",
          },
          body: JSON.stringify({
            recording_msid: recordingMSID,
            recording_mbid: recordingMBID,
            score,
          }),
        });
        if (!response.ok) {
          // Revert the feedback UI in case of failure
          setCurrentListenFeedback(0);
          throw response.statusText;
        }
      } catch (error) {
        newAlert(
          "danger",
          "Error while submitting feedback",
          error?.message ?? error.toString()
        );
      }
    }
  }
  const {
    children: dataSources,
    playerPaused,
    trackName,
    artistName,
    progressMs,
    durationMs,
    playPreviousTrack,
    togglePlay,
    playNextTrack,
    seekToPositionMs,
  } = props;

  const isPlayingATrack = Boolean(currentListen);

  return (
    <div id="brainz-player" aria-label="Playback control">
      <ProgressBar
        progressMs={progressMs}
        durationMs={durationMs}
        seekToPositionMs={seekToPositionMs}
      />
      <div className="content">
        <div className="cover-art">
          <div className="no-album-art" />
          {dataSources}
        </div>
        <div className={isPlayingATrack ? "currently-playing" : ""}>
          {trackName && (
            <div title={trackName} className="ellipsis-2-lines">
              {trackName}
            </div>
          )}
          {artistName && (
            <span className="small text-muted ellipsis" title={artistName}>
              {artistName}
            </span>
          )}
        </div>
      </div>
      <div className="controls">
        <PlaybackControlButton
          className="previous"
          title="Previous"
          action={playPreviousTrack}
          icon={faFastBackward}
        />
        <PlaybackControlButton
          className="play"
          action={togglePlay}
          title={`${playerPaused ? "Play" : "Pause"}`}
          icon={playerPaused ? faPlayCircle : faPauseCircle}
          size="2x"
        />
        <PlaybackControlButton
          className="next"
          action={playNextTrack}
          title="Next"
          icon={faFastForward}
        />
      </div>
      <div className="actions">
        <FontAwesomeIcon
          icon={faHeart}
          title="Love"
          onClick={
            isPlayingATrack
              ? () => submitFeedback(currentListenFeedback === 1 ? 0 : 1)
              : undefined
          }
          className={`${currentListenFeedback === 1 ? " loved" : ""}${
            !isPlayingATrack ? " disabled" : ""
          }`}
        />
        <FontAwesomeIcon
          icon={faHeartBroken}
          title="Hate"
          onClick={
            isPlayingATrack
              ? () => submitFeedback(currentListenFeedback === -1 ? 0 : -1)
              : undefined
          }
          className={`${currentListenFeedback === -1 ? " hated" : ""}${
            !isPlayingATrack ? " disabled" : ""
          }`}
        />
        <MenuOptions currentListen={currentListen} />
        {/* <FontAwesomeIcon icon={faCog} /> */}
      </div>
    </div>
  );
};

export default BrainzPlayerUI;
