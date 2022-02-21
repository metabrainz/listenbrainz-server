import * as React from "react";
import {
  faCog,
  faEllipsisV,
  faEye,
  faEyeSlash,
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
import { isNaN as _isNaN } from "lodash";

type PlaybackControlsProps = {
  playPreviousTrack: () => void;
  playNextTrack: (invert?: boolean) => void;
  togglePlay: (invert?: boolean) => void;
  playerPaused: boolean;
  trackName?: string;
  artistName?: string;
  progressMs: number;
  durationMs: number;
  seekToPositionMs: (msTimeCode: number) => void;
  currentFeedback: ListenFeedBack;
  submitFeedback: (score: ListenFeedBack) => Promise<void>;
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

type PlaybackControlsState = {};

export default class PlaybackControls extends React.Component<
  PlaybackControlsProps,
  PlaybackControlsState
> {
  // How many milliseconds to navigate to with keyboard left/right arrows
  keyboardStepMS: number = 5000;

  // constructor(props: PlaybackControlsProps) {
  //   super(props);
  //   this.state = {
  //   };
  // }

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
      currentFeedback,
      submitFeedback,
    } = this.props;

    const progressPercentage = Math.round(
      Number((progressMs * 100) / durationMs)
    );
    const isPlayingATrack = Boolean(trackName || artistName);
    const hideProgressBar =
      _isNaN(progressPercentage) || progressPercentage <= 0;
    return (
      <div id="brainz-player" aria-label="Playback control">
        <div
          className={`progress${hideProgressBar ? " hidden" : ""}`}
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
        <div className="content">
          <div className="cover-art">
            {children}
            <div className="no-album-art" />
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
            onClick={() => submitFeedback(currentFeedback === 1 ? 0 : 1)}
            className={`${currentFeedback === 1 ? " loved" : ""}`}
          />
          <FontAwesomeIcon
            icon={faHeartBroken}
            title="Hate"
            onClick={() => submitFeedback(currentFeedback === -1 ? 0 : -1)}
            className={`${currentFeedback === -1 ? " hated" : ""}`}
          />
          {/* <FontAwesomeIcon icon={faEllipsisV} />
          <FontAwesomeIcon icon={faCog} /> */}
        </div>
      </div>
    );
  }
}
