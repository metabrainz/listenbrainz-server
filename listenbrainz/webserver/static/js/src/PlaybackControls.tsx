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

export type SpotifyPlayDirection = "up" | "down" | "hidden";

type PlaybackControlsProps = {
  playPreviousTrack: () => void;
  playNextTrack: (invert?: boolean) => void;
  togglePlay: (invert?: boolean) => void;
  playerPaused: boolean;
  toggleDirection: () => void;
  direction: SpotifyPlayDirection;
  trackName?: string;
  artistName?: string;
  progressMs: number;
  durationMs: number;
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

export class PlaybackControls extends React.Component<
  PlaybackControlsProps,
  PlaybackControlsState
> {
  constructor(props: PlaybackControlsProps) {
    super(props);
    this.state = {
      autoHideControls: true,
    };
  }

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
    return (
      <div id="music-player" aria-label="Playback control">
        <div className="album">
          {children || <div className="noAlbumArt">No album art</div>}
        </div>
        <div
          className={`info ${
            !autoHideControls || !children || playerPaused ? "showControls" : ""
          }`}
        >
          <div className="currently-playing">
            <h2 className="song-name">{trackName || "—"}</h2>
            <h3 className="artist-name">{artistName}</h3>
            <div className="progress">
              <div
                className="progress-bar"
                style={{
                  width: `${(progressMs * 100) / durationMs}%`,
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
