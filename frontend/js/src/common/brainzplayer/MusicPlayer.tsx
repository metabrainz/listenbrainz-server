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
import { getAlbumArtFromListenMetadata } from "../../utils/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";

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

function CoverArtScrollWrapper({
  previousTrackCoverURL,
  currentTrackCoverURL,
  nextTrackCoverURL,
  musicPlayerCoverArtRef,
  playPreviousTrack,
  playNextTrack,
}: {
  previousTrackCoverURL?: string;
  currentTrackCoverURL?: string;
  nextTrackCoverURL?: string;
  musicPlayerCoverArtRef: React.RefObject<HTMLImageElement>;
  playPreviousTrack: () => void;
  playNextTrack: () => void;
}) {
  const coverArtScrollRef = React.useRef(null);
  const previousCoverArtRef = React.useRef(null);
  const currentCoverArtRef = React.useRef(null);
  const nextCoverArtRef = React.useRef(null);

  React.useEffect(() => {
    const options = {
      root: coverArtScrollRef.current,
      threshold: 0.5, // Adjust based on when you want to trigger the callback
    };

    const callback = (entries: IntersectionObserverEntry[]) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          if (entry.target === previousCoverArtRef.current) {
            console.log("previous");
            playPreviousTrack();
          } else if (entry.target === nextCoverArtRef.current) {
            console.log("next");
            playNextTrack();
          }
        }
      });
    };

    const observer = new IntersectionObserver(callback, options);

    const previousElem = previousCoverArtRef.current;
    const currentElem = currentCoverArtRef.current;
    const nextElem = nextCoverArtRef.current;

    if (previousElem) observer.observe(previousElem);
    if (currentElem) observer.observe(currentElem);
    if (nextElem) observer.observe(nextElem);

    return () => {
      if (previousElem) observer.unobserve(previousElem);
      if (currentElem) observer.unobserve(currentElem);
      if (nextElem) observer.unobserve(nextElem);
    };
  }, [
    previousTrackCoverURL,
    currentTrackCoverURL,
    nextTrackCoverURL,
    playPreviousTrack,
    playNextTrack,
  ]);

  return (
    <div className="cover-art-scroll-wrapper" ref={coverArtScrollRef}>
      {previousTrackCoverURL && (
        <div className="cover-art cover-art-wrapper" ref={previousCoverArtRef}>
          <img
            alt="coverart"
            className="img-responsive"
            src={previousTrackCoverURL}
            crossOrigin="anonymous"
          />
        </div>
      )}
      <div className="cover-art cover-art-wrapper" ref={currentCoverArtRef}>
        <img
          alt="coverart"
          className="img-responsive"
          src={currentTrackCoverURL}
          crossOrigin="anonymous"
          ref={musicPlayerCoverArtRef}
        />
      </div>
      {nextTrackCoverURL && (
        <div className="cover-art cover-art-wrapper" ref={nextCoverArtRef}>
          <img
            alt="coverart"
            className="img-responsive"
            src={nextTrackCoverURL}
            crossOrigin="anonymous"
          />
        </div>
      )}
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
      submitFeedback(currentListenFeedback === 1 ? 0 : 1);
    }
  }, [currentListenFeedback, isPlayingATrack, submitFeedback]);

  const submitDislikeFeedback = React.useCallback(() => {
    if (isPlayingATrack) {
      submitFeedback(currentListenFeedback === -1 ? 0 : -1);
    }
  }, [currentListenFeedback, isPlayingATrack, submitFeedback]);

  const coverArtScrollRef = React.useRef<HTMLDivElement>(null);

  const currentQueueIndex = React.useMemo(() => {
    return queue.findIndex((track) => track.id === currentListen?.id);
  }, [currentListen, queue]);

  // States to save previous and next track cover art URLs
  const [previousTrackCoverURL, setPreviousTrackCoverURL] = React.useState("");
  const [nextTrackCoverURL, setNextTrackCoverURL] = React.useState("");

  // Get previous and next track cover art URLs
  React.useEffect(() => {
    const getAndSetCoverArt = async (
      track: BrainzPlayerQueueItem,
      setCoverArt: any
    ) => {
      const coverArt = await getAlbumArtFromListenMetadata(
        track,
        spotifyAuth,
        APIService
      );
      setCoverArt(coverArt);
    };

    if (currentQueueIndex > 0) {
      getAndSetCoverArt(queue[currentQueueIndex - 1], setPreviousTrackCoverURL);
    } else {
      setPreviousTrackCoverURL("");
    }

    if (currentQueueIndex < queue.length - 1) {
      getAndSetCoverArt(queue[currentQueueIndex + 1], setNextTrackCoverURL);
    } else if (ambientQueue.length > 0) {
      getAndSetCoverArt(ambientQueue[0], setNextTrackCoverURL);
    } else {
      setNextTrackCoverURL("");
    }
  }, [APIService, ambientQueue, currentQueueIndex, queue, spotifyAuth]);

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
      <CoverArtScrollWrapper
        previousTrackCoverURL={previousTrackCoverURL}
        currentTrackCoverURL={currentTrackCoverURL}
        nextTrackCoverURL={nextTrackCoverURL}
        musicPlayerCoverArtRef={musicPlayerCoverArtRef}
        playPreviousTrack={playPreviousTrack}
        playNextTrack={playNextTrack}
      />
      {/* <div className="cover-art-scroll-wrapper" ref={coverArtScrollRef}>
            {previousTrackCoverURL && (
              <div className="cover-art cover-art-wrapper">
                <img
                  alt="coverart"
                  className="img-responsive"
                  src={previousTrackCoverURL}
                  crossOrigin="anonymous"
                />
              </div>
            )}
            <div className="cover-art cover-art-wrapper">
              <img
                alt="coverart"
                className="img-responsive"
                src={currentTrackCoverURL}
                ref={musicPlayerCoverArtRef}
                crossOrigin="anonymous"
              />
            </div>
            {nextTrackCoverURL && (
              <div className="cover-art cover-art-wrapper">
                <img
                  alt="coverart"
                  className="img-responsive"
                  src={nextTrackCoverURL}
                  crossOrigin="anonymous"
                />
              </div>
            )}
          </div> */}
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
