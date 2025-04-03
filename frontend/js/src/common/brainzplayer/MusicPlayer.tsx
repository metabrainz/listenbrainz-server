import {
  faChevronDown,
  faBackward,
  faHeart,
  faHeartCrack,
  faForward,
  faPlay,
  faPause,
  faBarsStaggered,
  faVolumeUp,
  faEllipsisVertical,
  faCompactDisc,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import { noop, throttle } from "lodash";
import {
  IconDefinition,
  IconProp,
  SizeProp,
} from "@fortawesome/fontawesome-svg-core";
import ProgressBar from "./ProgressBar";
import { useBrainzPlayerContext } from "./BrainzPlayerContext";
import { getAlbumArtFromListenMetadata } from "../../utils/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { FeedbackValue } from "./utils";
import MenuOptions from "./MenuOptions";

type PlaybackControlButtonProps = {
  className?: string;
  action: () => void;
  icon: IconDefinition;
  title: string;
  disabled?: boolean;
  color?: string;
  size?: SizeProp;
};

function PlaybackControlButton(props: PlaybackControlButtonProps) {
  const {
    className,
    action,
    icon,
    title,
    disabled,
    color,
    size = "2xl",
  } = props;
  return (
    <button
      className={`btn-transparent ${className ?? ""} ${
        disabled ? "disabled" : ""
      }`}
      title={title}
      onClick={disabled ? noop : action}
      type="button"
      tabIndex={0}
      data-testid={`bp-mp-${className}-button`}
    >
      <FontAwesomeIcon
        icon={icon as IconProp}
        size={size}
        fixedWidth
        color={color}
        title={title}
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
  const [animationDuration, setAnimationDuration] = React.useState(6);

  React.useEffect(() => {
    const checkOverflow = () => {
      if (textRef.current) {
        const overflowPixels =
          textRef.current.scrollWidth - textRef.current.clientWidth;
        setIsOverflowing(overflowPixels > 0);
        setAnimationDuration(Math.max(Math.round(overflowPixels / 20), 6));
      }
    };

    checkOverflow();
  }, [text]);

  return (
    <div ref={textRef} className="text-scroll-wrapper">
      <span
        className={`${className ?? ""} ${isOverflowing ? "animate" : ""}`}
        title={text}
        style={{ ...style, animationDuration: `${animationDuration}s` }}
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
  toggleShowVolume: () => void;
  seekToPositionMs: (msTimeCode: number) => void;
  toggleRepeatMode: () => void;
  submitFeedback: (score: ListenFeedBack) => Promise<void>;
  currentListenFeedback: number;
  musicPlayerCoverArtRef: React.RefObject<HTMLImageElement>;
  disabled?: boolean;
};

type FeedbackButtonsProps = {
  currentListenFeedback: number;
  isPlayingATrack: boolean;
  submitLikeFeedback: () => void;
  submitDislikeFeedback: () => void;
};

const FeedbackButtons = React.memo(
  ({
    currentListenFeedback,
    isPlayingATrack,
    submitLikeFeedback,
    submitDislikeFeedback,
  }: FeedbackButtonsProps) => (
    <>
      <PlaybackControlButton
        className={`love ${
          currentListenFeedback === FeedbackValue.LIKE ? " loved" : ""
        }${!isPlayingATrack ? " disabled" : ""}`}
        action={submitLikeFeedback}
        title="Love"
        icon={faHeart}
        size="xl"
      />
      <PlaybackControlButton
        className={`hate ${
          currentListenFeedback === FeedbackValue.DISLIKE ? " hated" : ""
        }${!isPlayingATrack ? " disabled" : ""}`}
        action={submitDislikeFeedback}
        title="Hate"
        icon={faHeartCrack}
        size="xl"
      />
    </>
  )
);

function MusicPlayer(props: MusicPlayerProps) {
  const {
    onHide,
    toggleQueue,
    playPreviousTrack,
    playNextTrack,
    togglePlay,
    toggleShowVolume,
    seekToPositionMs,
    toggleRepeatMode,
    submitFeedback,
    currentListenFeedback,
    musicPlayerCoverArtRef,
    disabled,
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
      const coverArt = await getAlbumArtFromListenMetadata(track, spotifyAuth);
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
        <div className="header-text">
          <AnimateTextOnOverflow
            text={currentTrackAlbum ?? "No track playing"}
          />
        </div>
        <MenuOptions
          currentListen={currentListen}
          iconElement={
            <PlaybackControlButton
              action={noop}
              title="More actions"
              icon={faEllipsisVertical}
              size="xl"
            />
          }
        />
      </div>
      <div className="cover-art-scroll-wrapper">
        <div className="cover-art cover-art-wrapper">
          {currentTrackCoverURL && (
            <img
              alt="coverart"
              className="img-responsive"
              src={currentTrackCoverURL}
              crossOrigin="anonymous"
              ref={musicPlayerCoverArtRef}
            />
          )}
          {!currentTrackCoverURL && (
            <FontAwesomeIcon
              style={{ fontSize: "16em" }}
              icon={faCompactDisc}
              opacity="15%"
              spin
            />
          )}
        </div>
      </div>
      <div className="info text-center">
        <div className="info-text-wrapper">
          <AnimateTextOnOverflow
            text={currentTrackName}
            style={{ fontSize: "1.5em" }}
          />
          <span
            className="ellipsis"
            title={currentTrackArtist}
            style={{ fontSize: "1em" }}
          >
            {currentTrackArtist}
          </span>
        </div>
        <ProgressBar seekToPositionMs={seekToPositionMs} showNumbers />
      </div>
      <div className="player-buttons">
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
          size="3x"
        />
        <PlaybackControlButton
          className="next"
          action={playNextTrack}
          title="Next"
          icon={faForward}
          disabled={disabled}
        />
      </div>
      <div className="player-buttons secondary">
        <FeedbackButtons
          currentListenFeedback={currentListenFeedback}
          isPlayingATrack={isPlayingATrack}
          submitLikeFeedback={submitLikeFeedback}
          submitDislikeFeedback={submitDislikeFeedback}
        />
        <PlaybackControlButton
          className="toggle-queue-button"
          action={toggleQueue}
          title="Queue"
          icon={faBarsStaggered}
          size="xl"
        />
        <PlaybackControlButton
          className={queueRepeatMode.title}
          action={toggleRepeatMode}
          title={queueRepeatMode.title}
          icon={queueRepeatMode.icon}
          color={queueRepeatMode.color}
          size="xl"
        />
        <PlaybackControlButton
          action={toggleShowVolume}
          title="Volume"
          icon={faVolumeUp}
          size="xl"
        />
      </div>
    </>
  );
}

export default React.memo(MusicPlayer);
