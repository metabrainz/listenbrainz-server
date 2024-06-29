import {
  faChevronDown,
  faBackward,
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
import { faHeart } from "@fortawesome/free-regular-svg-icons";
import ProgressBar from "./ProgressBar";
import { millisecondsToStr } from "../../playlists/utils";
import { useBrainzPlayerContext } from "./BrainzPlayerContext";

type PlaybackControlButtonProps = {
  className: string;
  action: () => void;
  icon: IconDefinition;
  title: string;
  size?: "2x";
  disabled?: boolean;
  color?: string;
};

function PlaybackControlButton(props: PlaybackControlButtonProps) {
  const { className, action, icon, title, size, disabled, color } = props;
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
    disabled,
  } = props;

  // BrainzPlayer Context
  const {
    currentTrackName,
    currentTrackArtist,
    currentTrackAlbum,
    currentTrackCoverURL,
    playerPaused,
    durationMs,
    progressMs,
    queueRepeatMode,
  } = useBrainzPlayerContext();

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

        <span>{currentTrackAlbum}</span>

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
          <span
            className="text-muted ellipsis"
            title={currentTrackName}
            style={{ fontSize: "1.5em" }}
          >
            {currentTrackName}
          </span>
          <span
            className="text-muted ellipsis"
            title={currentTrackArtist}
            style={{ fontSize: "1em" }}
          >
            {currentTrackArtist}
          </span>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "2.3em",
            gap: "1em",
          }}
        >
          <FontAwesomeIcon icon={faHeart} title="Love" className="love" />
          <FontAwesomeIcon icon={faHeartCrack} title="Hate" className="hate" />
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
          size="2x"
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
