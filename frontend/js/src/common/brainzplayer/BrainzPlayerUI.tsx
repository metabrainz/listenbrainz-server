import {
  faCog,
  faBarsStaggered,
  faFastBackward,
  faFastForward,
  faHeart,
  faHeartCrack,
  faMusic,
  faPauseCircle,
  faPlayCircle,
  faSlash,
} from "@fortawesome/free-solid-svg-icons";
import * as React from "react";

import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { toast } from "react-toastify";
import { noop } from "lodash";
import { Link } from "react-router-dom";
import { ToastMsg } from "../../notifications/Notifications";
import { millisecondsToStr } from "../../playlists/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getRecordingMBID, getRecordingMSID } from "../../utils/utils";
import MenuOptions from "./MenuOptions";
import ProgressBar from "./ProgressBar";
import {
  useBrainzPlayerContext,
  useBrainzPlayerDispatch,
} from "./BrainzPlayerContext";
import Queue from "./Queue";

type BrainzPlayerUIProps = {
  currentDataSourceName?: string;
  currentDataSourceIcon?: IconProp;
  playPreviousTrack: () => void;
  playNextTrack: (invert?: boolean) => void;
  togglePlay: (invert?: boolean) => void;
  playerPaused: boolean;
  trackName?: string;
  artistName?: string;
  trackUrl?: string;
  progressMs: number;
  durationMs: number;
  seekToPositionMs: (msTimeCode: number) => void;
  currentListen?: Listen | JSPFTrack;
  listenBrainzAPIBaseURI: string;
  disabled?: boolean;
  clearQueue: () => void;
};

type PlaybackControlButtonProps = {
  className: string;
  action: () => void;
  icon: IconDefinition;
  title: string;
  size?: "2x";
  disabled?: boolean;
};

function PlaybackControlButton(props: PlaybackControlButtonProps) {
  const { className, action, icon, title, size, disabled } = props;
  return (
    <button
      className={`btn-link ${className} ${disabled ? "disabled" : ""}`}
      title={title}
      onClick={disabled ? noop : action}
      type="button"
      tabIndex={0}
      data-testid={`bp-${className}-button`}
    >
      <FontAwesomeIcon icon={icon as IconProp} size={size} fixedWidth />
    </button>
  );
}

function BrainzPlayerUI(props: React.PropsWithChildren<BrainzPlayerUIProps>) {
  const {
    currentDataSourceName,
    currentDataSourceIcon,
    listenBrainzAPIBaseURI,
    currentListen,
    trackUrl,
  } = props;
  const [currentListenFeedback, setCurrentListenFeedback] = React.useState(0);
  const { currentUser } = React.useContext(GlobalAppContext);

  // BrainzPlayerContext
  const { queueRepeatMode } = useBrainzPlayerContext();
  const dispatch = useBrainzPlayerDispatch();

  // const { currentListenFeedback } = this.state;
  React.useEffect(() => {
    async function getFeedback() {
      // Get feedback for currentListen

      if (!currentUser?.name || !currentListen) {
        return;
      }
      const recordingMBID = getRecordingMBID(currentListen as Listen);
      const recordingMSID = getRecordingMSID(currentListen as Listen);

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

      const recordingMSID = getRecordingMSID(currentListen as Listen);
      const recordingMBID = getRecordingMBID(currentListen as Listen);

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
        toast.error(
          <ToastMsg
            title="Error while submitting feedback"
            message={error?.message ?? error.toString()}
          />,
          { toastId: "submit-feedback-error" }
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
    disabled,
    clearQueue,
  } = props;

  const isPlayingATrack = Boolean(currentListen);
  const recordingMSID = getRecordingMSID(currentListen as Listen);
  const recordingMBID = getRecordingMBID(currentListen as Listen);
  const showFeedback =
    (Boolean(recordingMSID) || Boolean(recordingMBID)) && isPlayingATrack;
  const playbackDisabledText = "Playback disabled in preferences";

  const [showQueue, setShowQueue] = React.useState(false);

  const toggleRepeatMode = () => {
    dispatch({ type: "TOGGLE_REPEAT_MODE" });
  };

  return (
    <>
      <div className={`queue ${showQueue ? "show" : ""}`}>
        <Queue clearQueue={clearQueue} onHide={() => setShowQueue(false)} />
      </div>
      <div
        id="brainz-player"
        aria-label="Playback control"
        data-testid="brainzplayer-ui"
      >
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
          {isPlayingATrack && (
            <div className="elapsed small text-muted">
              {millisecondsToStr(progressMs)}&#8239;/&#8239;
              {millisecondsToStr(durationMs)}
            </div>
          )}
        </div>
        <div
          className="controls"
          title={disabled ? playbackDisabledText : undefined}
        >
          <PlaybackControlButton
            className="previous"
            title="Previous"
            action={playPreviousTrack}
            icon={faFastBackward}
            disabled={disabled}
          />
          <PlaybackControlButton
            className="play"
            action={togglePlay}
            title={`${playerPaused ? "Play" : "Pause"}`}
            icon={playerPaused ? faPlayCircle : faPauseCircle}
            size="2x"
            disabled={disabled}
          />
          <PlaybackControlButton
            className="next"
            action={playNextTrack}
            title="Next"
            icon={faFastForward}
            disabled={disabled}
          />
        </div>
        <div className="actions">
          {isPlayingATrack && currentDataSourceName && (
            <a
              href={trackUrl || "#"}
              aria-label={`Open in ${currentDataSourceName}`}
              title={`Open in ${currentDataSourceName}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <FontAwesomeIcon icon={currentDataSourceIcon!} />
            </a>
          )}
          <FontAwesomeIcon
            icon={faBarsStaggered}
            style={{ color: showQueue ? "green" : "" }}
            onClick={() => setShowQueue((prevShowQueue) => !prevShowQueue)}
          />
          <FontAwesomeIcon
            icon={queueRepeatMode.icon}
            title={queueRepeatMode.title}
            style={{ color: queueRepeatMode.color }}
            onClick={toggleRepeatMode}
          />
          {showFeedback && (
            <>
              <FontAwesomeIcon
                icon={faHeart}
                title="Love"
                onClick={
                  isPlayingATrack
                    ? () => submitFeedback(currentListenFeedback === 1 ? 0 : 1)
                    : undefined
                }
                className={`love ${
                  currentListenFeedback === 1 ? " loved" : ""
                }${!isPlayingATrack ? " disabled" : ""}`}
              />
              <FontAwesomeIcon
                icon={faHeartCrack}
                title="Hate"
                onClick={
                  isPlayingATrack
                    ? () =>
                        submitFeedback(currentListenFeedback === -1 ? 0 : -1)
                    : undefined
                }
                className={`hate ${
                  currentListenFeedback === -1 ? " hated" : ""
                }${!isPlayingATrack ? " disabled" : ""}`}
              />
            </>
          )}
          {disabled ? (
            <span className="fa-layers fa-fw" title={playbackDisabledText}>
              <FontAwesomeIcon icon={faMusic} />
              <FontAwesomeIcon icon={faSlash} />
            </span>
          ) : (
            <MenuOptions currentListen={currentListen} />
          )}
          <Link to="/settings/brainzplayer/">
            <FontAwesomeIcon icon={faCog} title="Player preferences" />
          </Link>
        </div>
      </div>
    </>
  );
}

export default React.memo(BrainzPlayerUI);
