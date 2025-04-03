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
  faVolumeUp,
  faMaximize,
} from "@fortawesome/free-solid-svg-icons";
import * as React from "react";

import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { toast } from "react-toastify";
import { noop } from "lodash";
import { Link } from "react-router-dom";
import { Vibrant as VibrantLibrary } from "node-vibrant/browser";
import type { Palette } from "@vibrant/color";
import tinycolor from "tinycolor2";
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
import MusicPlayer from "./MusicPlayer";
import { FeedbackValue } from "./utils";
import VolumeControlButton from "./VolumeControlButton";
import { COLOR_LB_BLUE, COLOR_LB_ORANGE } from "../../utils/constants";
import { DataSourceType } from "./BrainzPlayer";

type BrainzPlayerUIProps = {
  currentDataSource?: DataSourceType | null;
  playPreviousTrack: () => void;
  playNextTrack: (invert?: boolean) => void;
  togglePlay: (invert?: boolean) => void;

  seekToPositionMs: (msTimeCode: number) => void;
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
    listenBrainzAPIBaseURI,
    children: dataSources,
    playPreviousTrack,
    togglePlay,
    playNextTrack,
    seekToPositionMs,
    disabled,
    clearQueue,
    currentDataSource,
  } = props;
  const [currentListenFeedback, setCurrentListenFeedback] = React.useState(0);
  const [isMobile, setIsMobile] = React.useState(false);
  const { currentUser } = React.useContext(GlobalAppContext);

  // BrainzPlayerContext
  const brainzPlayerContext = useBrainzPlayerContext();
  const brainzPlayerContextRef = React.useRef(brainzPlayerContext);
  brainzPlayerContextRef.current = brainzPlayerContext;

  const dispatch = useBrainzPlayerDispatch();

  React.useEffect(() => {
    async function getFeedback() {
      // Get feedback for currentListen

      if (!currentUser?.name || !brainzPlayerContextRef.current.currentListen) {
        return;
      }
      const recordingMBID = getRecordingMBID(
        brainzPlayerContextRef.current.currentListen as Listen
      );
      const recordingMSID = getRecordingMSID(
        brainzPlayerContextRef.current.currentListen as Listen
      );

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
  }, [
    brainzPlayerContextRef.current.currentListen,
    currentUser.name,
    listenBrainzAPIBaseURI,
  ]);

  React.useEffect(() => {
    // Also check the width on first render
    setIsMobile(/Mobi/.test(navigator.userAgent));

    const handleResize = () => {
      setIsMobile(/Mobi/.test(navigator.userAgent));
    };
    window.addEventListener("resize", handleResize);
  }, []);

  const submitFeedback = React.useCallback(
    async (score: ListenFeedBack) => {
      if (currentUser?.auth_token) {
        setCurrentListenFeedback(score);

        const recordingMSID = getRecordingMSID(
          brainzPlayerContextRef.current.currentListen as Listen
        );
        const recordingMBID = getRecordingMBID(
          brainzPlayerContextRef.current.currentListen as Listen
        );

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
    },
    [currentUser.auth_token, listenBrainzAPIBaseURI]
  );

  const isPlayingATrack = Boolean(brainzPlayerContextRef.current.currentListen);
  const recordingMSID = getRecordingMSID(
    brainzPlayerContextRef.current.currentListen as Listen
  );
  const recordingMBID = getRecordingMBID(
    brainzPlayerContextRef.current.currentListen as Listen
  );
  const showFeedback =
    (Boolean(recordingMSID) || Boolean(recordingMBID)) && isPlayingATrack;
  const playbackDisabledText = "Playback disabled in preferences";

  const [showQueue, setShowQueue] = React.useState(false);
  const [showVolume, setShowVolume] = React.useState(false);
  const [showMusicPlayer, setShowMusicPlayer] = React.useState(false);

  const toggleShowVolume = () => {
    setShowVolume((prevValue) => !prevValue);
  };

  const [musicPlayerColorPalette, setMusicPlayerColorPalette] = React.useState<
    Palette
  >();

  const toggleQueue = React.useCallback(() => {
    setShowQueue((prevShowQueue) => !prevShowQueue);
  }, []);

  const toggleMusicPlayer = React.useCallback(() => {
    setShowMusicPlayer((prevShow) => !prevShow);
  }, []);

  const toggleRepeatMode = React.useCallback(() => {
    dispatch({ type: "TOGGLE_REPEAT_MODE" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const musicPlayerCoverArtRef = React.useRef<HTMLImageElement>(null);

  React.useEffect(() => {
    if (!brainzPlayerContextRef.current.currentTrackCoverURL) {
      return;
    }
    VibrantLibrary.from(brainzPlayerContextRef.current.currentTrackCoverURL)
      .getPalette()
      .then((palette) => {
        setMusicPlayerColorPalette(palette);
      });
  }, [brainzPlayerContextRef.current.currentTrackCoverURL]);

  let musicPlayerBackground = `linear-gradient(to bottom, ${COLOR_LB_BLUE} 30%, ${COLOR_LB_ORANGE})`;
  let musicPlayerTextColor1 = "white";
  let musicPlayerTextColor2 = "white";
  let musicPlayerTextColor3 = "white";

  if (musicPlayerColorPalette) {
    const {
      Vibrant,
      DarkVibrant,
      LightVibrant,
      Muted,
      DarkMuted,
      LightMuted,
    } = musicPlayerColorPalette;

    musicPlayerBackground = `linear-gradient(to bottom, ${Vibrant?.hex} 60%, ${DarkVibrant?.hex})`;

    musicPlayerTextColor1 = tinycolor
      .mostReadable(Vibrant!.hex, [
        Muted!.hex,
        LightMuted!.hex,
        LightVibrant!.hex,
        DarkMuted!.hex,
      ])
      .toHexString();

    musicPlayerTextColor2 = tinycolor
      .mostReadable(DarkVibrant!.hex, [
        Muted!.hex,
        LightMuted!.hex,
        LightVibrant!.hex,
        DarkMuted!.hex,
      ])
      .toHexString();

    musicPlayerTextColor3 = DarkMuted!.hex;

    // Ensure the choice of colours was reasonable, use black or white instead if not readable
    if (!tinycolor.isReadable(musicPlayerTextColor1, Vibrant!.hex)) {
      musicPlayerTextColor1 = Vibrant!.bodyTextColor;
    }
    if (
      !tinycolor.isReadable(musicPlayerTextColor2, DarkVibrant!.hex, {
        size: "large",
      })
    ) {
      musicPlayerTextColor2 = DarkVibrant!.bodyTextColor;
    }
  }

  return (
    <>
      <div className={`volume ${showVolume ? "show" : ""}`}>
        <VolumeControlButton />
      </div>
      <div
        className={`music-player ${showMusicPlayer ? "open" : ""}`}
        style={
          {
            "--music-player-background": musicPlayerBackground,
            "--music-player-text-color-1": musicPlayerTextColor1,
            "--music-player-text-color-2": musicPlayerTextColor2,
            "--music-player-accent-color": musicPlayerTextColor3,
          } as React.CSSProperties
        }
      >
        <MusicPlayer
          onHide={toggleMusicPlayer}
          toggleQueue={toggleQueue}
          playPreviousTrack={playPreviousTrack}
          playNextTrack={playNextTrack}
          togglePlay={togglePlay}
          toggleShowVolume={toggleShowVolume}
          seekToPositionMs={seekToPositionMs}
          toggleRepeatMode={toggleRepeatMode}
          submitFeedback={submitFeedback}
          currentListenFeedback={currentListenFeedback}
          musicPlayerCoverArtRef={musicPlayerCoverArtRef}
          disabled={disabled}
        />
      </div>
      <div className={`queue ${showQueue ? "show" : ""}`}>
        <Queue clearQueue={clearQueue} onHide={() => setShowQueue(false)} />
      </div>
      <div
        id="brainz-player"
        className={isPlayingATrack ? "playing" : ""}
        aria-label="Playback control"
        data-testid="brainzplayer-ui"
      >
        {!showMusicPlayer && (
          <ProgressBar seekToPositionMs={seekToPositionMs} />
        )}
        <div className="content">
          {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */}
          <div
            className="cover-art"
            onClick={isMobile ? toggleMusicPlayer : noop}
          >
            <div className="no-album-art" />
            {dataSources}
          </div>
          <div className={isPlayingATrack ? "currently-playing" : ""}>
            {brainzPlayerContextRef.current.currentTrackName && (
              <div
                title={brainzPlayerContextRef.current.currentTrackName}
                className="ellipsis-2-lines"
              >
                {brainzPlayerContextRef.current.currentTrackName}
              </div>
            )}
            {brainzPlayerContextRef.current.currentTrackArtist && (
              <span
                className="small text-muted ellipsis"
                title={brainzPlayerContextRef.current.currentTrackArtist}
              >
                {brainzPlayerContextRef.current.currentTrackArtist}
              </span>
            )}
          </div>
          {isPlayingATrack && !isMobile && (
            <div className="elapsed small text-muted">
              {millisecondsToStr(brainzPlayerContextRef.current.progressMs)}
              &#8239;/&#8239;
              {millisecondsToStr(brainzPlayerContextRef.current.durationMs)}
            </div>
          )}
        </div>
        <div
          className="controls"
          title={disabled ? playbackDisabledText : undefined}
        >
          {!isMobile && (
            <PlaybackControlButton
              className="previous"
              title="Previous"
              action={playPreviousTrack}
              icon={faFastBackward}
              disabled={disabled}
            />
          )}
          <PlaybackControlButton
            className="play"
            action={togglePlay}
            title={`${
              brainzPlayerContextRef.current.playerPaused ? "Play" : "Pause"
            }`}
            icon={
              brainzPlayerContextRef.current.playerPaused
                ? faPlayCircle
                : faPauseCircle
            }
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
          {isPlayingATrack && currentDataSource?.name && (
            <>
              <a
                href={brainzPlayerContextRef.current.currentTrackURL || "#"}
                className="music-service-icon"
                aria-label={`Open in ${currentDataSource.name}`}
                title={`Open in ${currentDataSource.name}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <FontAwesomeIcon
                  icon={currentDataSource.icon}
                  color={currentDataSource.iconColor}
                />
              </a>
              {!isMobile && (
                <FontAwesomeIcon
                  icon={faVolumeUp}
                  style={{ color: showVolume ? "green" : "" }}
                  onClick={() => setShowVolume(!showVolume)}
                />
              )}
            </>
          )}
          {isMobile ? (
            <FontAwesomeIcon icon={faMaximize} onClick={toggleMusicPlayer} />
          ) : (
            <FontAwesomeIcon icon={faBarsStaggered} onClick={toggleQueue} />
          )}

          {!isMobile && (
            <FontAwesomeIcon
              icon={brainzPlayerContextRef.current.queueRepeatMode.icon}
              title={brainzPlayerContextRef.current.queueRepeatMode.title}
              style={{
                color: brainzPlayerContextRef.current.queueRepeatMode.color,
              }}
              onClick={toggleRepeatMode}
            />
          )}
          {showFeedback && !isMobile && (
            <>
              <FontAwesomeIcon
                icon={faHeart}
                title="Love"
                onClick={
                  isPlayingATrack
                    ? () =>
                        submitFeedback(
                          currentListenFeedback === FeedbackValue.LIKE
                            ? FeedbackValue.NEUTRAL
                            : FeedbackValue.LIKE
                        )
                    : undefined
                }
                className={`love ${
                  currentListenFeedback === FeedbackValue.LIKE ? " loved" : ""
                }${!isPlayingATrack ? " disabled" : ""}`}
              />
              <FontAwesomeIcon
                icon={faHeartCrack}
                title="Hate"
                onClick={
                  isPlayingATrack
                    ? () =>
                        submitFeedback(
                          currentListenFeedback === FeedbackValue.DISLIKE
                            ? FeedbackValue.NEUTRAL
                            : FeedbackValue.DISLIKE
                        )
                    : undefined
                }
                className={`hate ${
                  currentListenFeedback === FeedbackValue.DISLIKE
                    ? " hated"
                    : ""
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
            !isMobile && (
              <MenuOptions
                currentListen={brainzPlayerContextRef.current.currentListen}
              />
            )
          )}
          {!isMobile && (
            <Link to="/settings/brainzplayer/">
              <FontAwesomeIcon icon={faCog} title="Player preferences" />
            </Link>
          )}
        </div>
      </div>
    </>
  );
}

export default React.memo(BrainzPlayerUI);
