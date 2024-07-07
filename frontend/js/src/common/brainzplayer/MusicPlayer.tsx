import {
  faChevronDown,
  faBackward,
  faHeart,
  faHeartCrack,
  faForward,
  faPlay,
  faPause,
  faEllipsis,
  faBarsStaggered,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import { noop } from "lodash";
import { IconDefinition, IconProp } from "@fortawesome/fontawesome-svg-core";
import ProgressBar from "./ProgressBar";
import { millisecondsToStr } from "../../playlists/utils";
import { useBrainzPlayerContext } from "./BrainzPlayerContext";

type PlaybackControlButtonProps = {
  className: string;
  action: () => void;
  icon: IconDefinition;
  title: string;
  disabled?: boolean;
  color?: string;
};

function PlaybackControlButton(props: PlaybackControlButtonProps) {
  const { className, action, icon, title, disabled, color } = props;
  return (
    <button
      className={`btn-transparent ${className} ${disabled ? "disabled" : ""}`}
      title={title}
      onClick={disabled ? noop : action}
      type="button"
      tabIndex={0}
      data-testid={`bp-mp-${className}-button`}
    >
      <FontAwesomeIcon
        icon={icon as IconProp}
        size="2xl"
        fixedWidth
        style={{
          fontSize: "xx-large",
        }}
        color={color}
      />
    </button>
  );
}

type MusicPlayerProps = {
  onHide: () => void;
  toggleQueue: () => void;
  playPreviousTrack: () => void;
  playNextTrack: (invert?: boolean) => void;
  togglePlay: (invert?: boolean) => void;
  seekToPositionMs: (msTimeCode: number) => void;
  toggleRepeatMode: () => void;
  submitFeedback: (score: ListenFeedBack) => Promise<void>;
  currentListenFeedback: number;
  disabled?: boolean;
};

function MusicPlayer(props: MusicPlayerProps) {
  const {
    onHide,
    toggleQueue,
    playPreviousTrack,
    playNextTrack,
    togglePlay,
    seekToPositionMs,
    toggleRepeatMode,
    submitFeedback,
    currentListenFeedback,
    disabled,
  } = props;

  // BrainzPlayer Context
  const {
    currentListen,
    currentTrackName,
    currentTrackArtist,
    currentTrackAlbum,
    currentTrackCoverURL,
    playerPaused,
    durationMs,
    progressMs,
    queueRepeatMode,
  } = useBrainzPlayerContext();

  const isPlayingATrack = React.useMemo(() => !!currentListen, [currentListen]);

  const submitLikeFeedback = React.useCallback(() => {
    if (isPlayingATrack) {
      submitFeedback(currentListenFeedback === 1 ? 0 : 1);
    }
  }, [currentListenFeedback, isPlayingATrack, submitFeedback]);

  const submitDislikeFeedback = React.useCallback(() => {
    if (isPlayingATrack) {
      submitFeedback(currentListenFeedback === -1 ? 0 : -1);
    }
  }, [currentListenFeedback, isPlayingATrack, submitFeedback]);

  return (
    <>
      <div className="header">
        <FontAwesomeIcon
          className="btn hide-queue"
          icon={faChevronDown}
          title="Hide queue"
          style={{
            fontSize: "x-large",
          }}
          onClick={onHide}
        />
        <div className="text-scroll-wrapper">
          <span>{currentTrackAlbum}</span>
        </div>

        <FontAwesomeIcon
          className="btn toggle-info"
          icon={faEllipsis}
          title="Hide queue"
          style={{
            fontSize: "x-large",
          }}
        />
      </div>
      <div className="cover-art cover-art-wrapper">
        <img
          alt="coverart"
          className="img-responsive"
          src={currentTrackCoverURL}
        />
      </div>
      <div className="info">
        <div className="info-text-wrapper">
          <div className="text-scroll-wrapper">
            <span
              className="text-muted"
              title={currentTrackName}
              style={{ fontSize: "1.5em" }}
            >
              {currentTrackName}
            </span>
          </div>
          <span
            className="text-muted ellipsis"
            title={currentTrackArtist}
            style={{ fontSize: "1em" }}
          >
            {currentTrackArtist}
          </span>
        </div>
        <div className="feedback-buttons-wrapper">
          <FontAwesomeIcon
            icon={faHeart}
            title="Love"
            className={`love ${currentListenFeedback === 1 ? " loved" : ""}${
              !isPlayingATrack ? " disabled" : ""
            }`}
            onClick={submitLikeFeedback}
          />
          <FontAwesomeIcon
            icon={faHeartCrack}
            title="Hate"
            className={`hate ${currentListenFeedback === -1 ? " hated" : ""}${
              !isPlayingATrack ? " disabled" : ""
            }`}
            onClick={submitDislikeFeedback}
          />
        </div>
      </div>
      <div className="progress-bar-wrapper">
        <ProgressBar
          progressMs={progressMs}
          durationMs={durationMs}
          seekToPositionMs={seekToPositionMs}
        />
        <div className="elapsed small text-muted">
          {millisecondsToStr(progressMs)}&#8239;/&#8239;
          {millisecondsToStr(durationMs)}
        </div>
      </div>
      <div className="player-buttons">
        <PlaybackControlButton
          className="toggle-queue-button"
          action={toggleQueue}
          title="Queue"
          icon={faBarsStaggered}
        />
        <PlaybackControlButton
          className="previous"
          title="Previous"
          action={playPreviousTrack}
          icon={faBackward}
          disabled={disabled}
        />
        <PlaybackControlButton
          className="play"
          action={togglePlay}
          title={`${playerPaused ? "Play" : "Pause"}`}
          icon={playerPaused ? faPlay : faPause}
          disabled={disabled}
        />
        <PlaybackControlButton
          className="next"
          action={playNextTrack}
          title="Next"
          icon={faForward}
          disabled={disabled}
        />
        <PlaybackControlButton
          className={queueRepeatMode.title}
          action={toggleRepeatMode}
          title={queueRepeatMode.title}
          icon={queueRepeatMode.icon}
          color={queueRepeatMode.color}
        />
      </div>
    </>
  );
}

export default React.memo(MusicPlayer);
