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
import {
  QueueRepeatMode,
  useBrainzPlayerDispatch,
} from "./BrainzPlayerContext";

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
      data-testid={`bp-${className}-button`}
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
  trackName: string;
  artistName: string;
  progressMs: number;
  queueRepeatMode: QueueRepeatMode;
  durationMs: number;
  playerPaused: boolean;
  disabled?: boolean;
};

export default function MusicPlayer(props: MusicPlayerProps) {
  const {
    onHide,
    toggleQueue,
    playPreviousTrack,
    playNextTrack,
    togglePlay,
    seekToPositionMs,
    trackName,
    artistName,
    queueRepeatMode,
    progressMs,
    durationMs,
    playerPaused,
    disabled,
  } = props;

  // BrainzPlayer Context
  const dispatch = useBrainzPlayerDispatch();

  const toggleRepeatMode = () => {
    dispatch({ type: "TOGGLE_REPEAT_MODE" });
  };

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

        <span>Album Name / Playlist Name</span>

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
          src="https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/fe/c6/13/fec61345-4a34-8056-aff4-77d7ee71fabf/SameBeef_Inlay-_Itunes.jpg/600x600bb.jpg"
        />
      </div>
      <div className="info">
        <div className="info-text-wrapper">
          <span
            className="text-muted ellipsis"
            title={trackName}
            style={{ fontSize: "1.5em" }}
          >
            {trackName}
          </span>
          <span
            className="text-muted ellipsis"
            title={artistName}
            style={{ fontSize: "1em" }}
          >
            {artistName}
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
