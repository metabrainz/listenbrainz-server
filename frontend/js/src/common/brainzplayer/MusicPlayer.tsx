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
import { noop, throttle } from "lodash";
import { IconDefinition, IconProp } from "@fortawesome/fontawesome-svg-core";
import ProgressBar from "./ProgressBar";
import { millisecondsToStr } from "../../playlists/utils";
import { useBrainzPlayerContext } from "./BrainzPlayerContext";
import { getAlbumArtFromListenMetadata } from "../../utils/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { FeedbackValue } from "./utils";

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

function AnimateTextOnOverflow(props: {
  text?: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  const { text, className, style } = props;
  const textRef = React.useRef<HTMLDivElement>(null);
  const [isOverflowing, setIsOverflowing] = React.useState(false);

  React.useEffect(() => {
    const checkOverflow = () => {
      if (textRef.current) {
        setIsOverflowing(
          textRef.current.scrollWidth > textRef.current.clientWidth
        );
      }
    };

    checkOverflow();
  }, [text]);

  return (
    <div ref={textRef} className="text-scroll-wrapper">
      <span
        className={`${className} ${isOverflowing ? "animate" : ""}`}
        title={text}
        style={style}
      >
        {text}
      </span>
    </div>
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
  musicPlayerCoverArtRef: React.RefObject<HTMLImageElement>;
  disabled?: boolean;
  mostReadableTextColor: string;
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
    musicPlayerCoverArtRef,
    disabled,
    mostReadableTextColor,
  } = props;

  // BrainzPlayer Context
  const {
    currentListen,
    currentListenIndex,
    currentTrackName,
    currentTrackArtist,
    currentTrackAlbum,
    currentTrackCoverURL,
    playerPaused,
    durationMs,
    progressMs,
    queueRepeatMode,
    queue,
    ambientQueue,
  } = useBrainzPlayerContext();

  // Global App Context
  const { spotifyAuth, APIService } = React.useContext(GlobalAppContext);

  const isPlayingATrack = React.useMemo(() => !!currentListen, [currentListen]);

  const submitLikeFeedback = React.useCallback(() => {
    if (isPlayingATrack) {
      submitFeedback(
        currentListenFeedback === FeedbackValue.LIKE
          ? FeedbackValue.NEUTRAL
          : FeedbackValue.LIKE
      );
    }
  }, [currentListenFeedback, isPlayingATrack, submitFeedback]);

  const submitDislikeFeedback = React.useCallback(() => {
    if (isPlayingATrack) {
      submitFeedback(
        currentListenFeedback === FeedbackValue.DISLIKE
          ? FeedbackValue.NEUTRAL
          : FeedbackValue.DISLIKE
      );
    }
  }, [currentListenFeedback, isPlayingATrack, submitFeedback]);

  // States to save previous and next track cover art URLs
  const [previousTrackCoverURL, setPreviousTrackCoverURL] = React.useState("");
  const [nextTrackCoverURL, setNextTrackCoverURL] = React.useState("");

  // Get previous and next track cover art URLs
  React.useEffect(() => {
    const getAndSetCoverArt = async (
      track: BrainzPlayerQueueItem,
      setCoverArt: React.Dispatch<React.SetStateAction<string>>
    ) => {
      const coverArt = await getAlbumArtFromListenMetadata(
        track,
        spotifyAuth,
        APIService
      );
      setCoverArt(coverArt ?? "");
    };

    if (currentListenIndex > 0) {
      getAndSetCoverArt(
        queue[currentListenIndex - 1],
        setPreviousTrackCoverURL
      );
    } else {
      setPreviousTrackCoverURL("");
    }

    if (currentListenIndex < queue.length - 1) {
      getAndSetCoverArt(queue[currentListenIndex + 1], setNextTrackCoverURL);
    } else if (ambientQueue.length > 0) {
      getAndSetCoverArt(ambientQueue[0], setNextTrackCoverURL);
    } else {
      setNextTrackCoverURL("");
    }
  }, [APIService, ambientQueue, currentListenIndex, queue, spotifyAuth]);

  const COVERART_PLACEHOLDER = "/static/img/cover-art-placeholder.jpg";

  return (
    <>
      <div className="header">
        <FontAwesomeIcon
          className="btn hide-queue"
          icon={faChevronDown}
          title="Hide queue"
          style={{
            fontSize: "x-large",
            padding: "5px 10px",
          }}
          onClick={onHide}
        />
        <AnimateTextOnOverflow text={currentTrackAlbum} />

        <FontAwesomeIcon
          className="btn toggle-info"
          icon={faEllipsis}
          title="Hide queue"
          style={{
            fontSize: "x-large",
            padding: "5px 10px",
          }}
        />
      </div>
      <div className="cover-art-scroll-wrapper">
        <div className="cover-art cover-art-wrapper">
          <img
            alt="coverart"
            className="img-responsive"
            src={currentTrackCoverURL || COVERART_PLACEHOLDER}
            crossOrigin="anonymous"
            ref={musicPlayerCoverArtRef}
          />
        </div>
      </div>
      <div className="info">
        <div className="info-text-wrapper">
          <AnimateTextOnOverflow
            className="text-muted"
            text={currentTrackName}
            style={{ fontSize: "1.5em" }}
          />
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
            className={`love ${
              currentListenFeedback === FeedbackValue.LIKE ? " loved" : ""
            }${!isPlayingATrack ? " disabled" : ""}`}
            onClick={submitLikeFeedback}
          />
          <FontAwesomeIcon
            icon={faHeartCrack}
            title="Hate"
            className={`hate ${
              currentListenFeedback === FeedbackValue.DISLIKE ? " hated" : ""
            }${!isPlayingATrack ? " disabled" : ""}`}
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
        <div style={{ color: mostReadableTextColor }}>
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
