import * as React from "react";
import {
  faEye,
  faEyeSlash,
  faFastBackward,
  faFastForward,
  faPauseCircle,
  faPlayCircle,
  faSortAmountDown,
  faSortAmountUp,
} from "@fortawesome/free-solid-svg-icons";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { IconProp } from "@fortawesome/fontawesome-svg-core";

type PlaybackControlsProps = {
  playPreviousTrack: () => void;
  playNextTrack: (invert?: boolean) => void;
  togglePlay: (invert?: boolean) => void;
  playerPaused: boolean;
  toggleDirection: () => void;
  direction: BrainzPlayDirection;
  trackName?: string;
  artistName?: string;
  progressMs: number;
  durationMs: number;
  seekToPositionMs: (msTimeCode: number) => void;
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

type PlaybackControlsState = {
  autoHideControls: boolean;
};

export default class PlaybackControls extends React.Component<
  PlaybackControlsProps,
  PlaybackControlsState
> {
  // How many milliseconds to navigate to with keyboard left/right arrows
  keyboardStepMS: number = 5000;

  constructor(props: PlaybackControlsProps) {
    super(props);
    this.state = {
      autoHideControls: true,
    };
  }

  progressClickHandler = (event: React.MouseEvent<HTMLInputElement>): void => {
    const { durationMs, seekToPositionMs } = this.props;
    const progressBarBoundingRect = event.currentTarget.getBoundingClientRect();
    const progressBarWidth = progressBarBoundingRect.width;
    const musicPlayerXOffset = progressBarBoundingRect.x;
    const absoluteClickXPos = event.clientX;
    const relativeClickXPos = absoluteClickXPos - musicPlayerXOffset;
    const percentPos = relativeClickXPos / progressBarWidth;
    const positionMs = Math.round(durationMs * percentPos);
    seekToPositionMs(positionMs);
  };

  onKeyPressHandler = (event: React.KeyboardEvent<HTMLInputElement>): void => {
    const {
      durationMs,
      progressMs,
      seekToPositionMs,
      playNextTrack,
      playPreviousTrack,
    } = this.props;
    if (event.key === "ArrowLeft") {
      if (event.shiftKey) {
        playPreviousTrack();
        return;
      }
      const oneStepEarlier = progressMs - this.keyboardStepMS;
      seekToPositionMs(oneStepEarlier > 0 ? oneStepEarlier : 0);
    }
    if (event.key === "ArrowRight") {
      if (event.shiftKey) {
        playNextTrack();
        return;
      }
      const oneStepLater = progressMs + this.keyboardStepMS;
      if (oneStepLater <= durationMs - 500) {
        seekToPositionMs(oneStepLater);
      }
    }
  };

  render() {
    const {
      children,
      playerPaused,
      trackName,
      artistName,
      progressMs,
      durationMs,
      playPreviousTrack,
      togglePlay,
      playNextTrack,
      toggleDirection,
      direction,
    } = this.props;

    const { autoHideControls } = this.state;
    const progressPercentage = Number((progressMs * 100) / durationMs);
    return (
      <div id="music-player" aria-label="Playback control">
        <div className="content">
          {children}
          <div className="no-album-art" />
        </div>
        <div
          className={`info ${
            !autoHideControls || !children || playerPaused ? "showControls" : ""
          }`}
        >
          <div className="currently-playing">
            {trackName && <h2 className="song-name">{trackName}</h2>}
            {artistName && <h3 className="artist-name">{artistName}</h3>}
            <div
              className="progress"
              onClick={this.progressClickHandler}
              onKeyDown={this.onKeyPressHandler}
              aria-label="Audio Progress Control"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progressPercentage}
              tabIndex={0}
            >
              <div
                className="progress-bar"
                style={{
                  width: `${progressPercentage}%`,
                }}
              />
            </div>
          </div>
          <div className="controls">
            <PlaybackControlButton
              className="left btn btn-xs"
              title={`${
                autoHideControls ? "Always show" : "Autohide"
              } controls`}
              action={() => {
                this.setState((state) => ({
                  autoHideControls: !state.autoHideControls,
                }));
              }}
              icon={autoHideControls ? faEyeSlash : faEye}
            />
            <PlaybackControlButton
              className="previous btn btn-xs"
              title="Previous"
              action={playPreviousTrack}
              icon={faFastBackward}
            />
            <PlaybackControlButton
              className="play btn"
              action={togglePlay}
              title={`${playerPaused ? "Play" : "Pause"}`}
              icon={playerPaused ? faPlayCircle : faPauseCircle}
              size="2x"
            />
            <PlaybackControlButton
              className="next btn btn-xs"
              action={playNextTrack}
              title="Next"
              icon={faFastForward}
            />
            {direction !== "hidden" && (
              <PlaybackControlButton
                className="right btn btn-xs"
                action={toggleDirection}
                title={`Play ${direction === "up" ? "down" : "up"}`}
                icon={direction === "up" ? faSortAmountUp : faSortAmountDown}
              />
            )}
          </div>
        </div>
      </div>
    );
  }
}
