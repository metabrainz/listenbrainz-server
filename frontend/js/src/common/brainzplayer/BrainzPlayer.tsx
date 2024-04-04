import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faPlayCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  has as _has,
  isEqual as _isEqual,
  isNil as _isNil,
  isString as _isString,
  throttle as _throttle,
  assign,
  cloneDeep,
  debounce,
  omit,
} from "lodash";
import * as React from "react";
import { toast } from "react-toastify";
import {
  ToastMsg,
  createNotification,
  hasMediaSessionSupport,
  hasNotificationPermission,
  overwriteMediaSession,
  updateMediaSession,
  updateWindowTitle,
} from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getArtistName, getTrackName } from "../../utils/utils";
import BrainzPlayerUI from "./BrainzPlayerUI";
import SoundcloudPlayer from "./SoundcloudPlayer";
import SpotifyPlayer from "./SpotifyPlayer";
import YoutubePlayer from "./YoutubePlayer";
import {
  useBrainzPlayerContext,
  useBrainzPlayerDispatch,
} from "./BrainzPlayerContext";

export type DataSourceType = {
  name: string;
  icon: IconProp;
  playListen: (listen: Listen | JSPFTrack) => void;
  togglePlay: () => void;
  seekToPositionMs: (msTimecode: number) => void;
  canSearchAndPlayTracks: () => boolean;
  datasourceRecordsListens: () => boolean;
};

export type DataSourceTypes = SpotifyPlayer | YoutubePlayer | SoundcloudPlayer;

export type DataSourceProps = {
  show: boolean;
  playerPaused: boolean;
  onPlayerPausedChange: (paused: boolean) => void;
  onProgressChange: (progressMs: number) => void;
  onDurationChange: (durationMs: number) => void;
  onTrackInfoChange: (
    title: string,
    trackURL: string,
    artist?: string,
    album?: string,
    artwork?: Array<MediaImage>
  ) => void;
  onTrackEnd: () => void;
  onTrackNotFound: () => void;
  handleError: (error: BrainzPlayerError, title: string) => void;
  handleWarning: (message: string | JSX.Element, title: string) => void;
  handleSuccess: (message: string | JSX.Element, title: string) => void;
  onInvalidateDataSource: (
    dataSource?: DataSourceTypes,
    message?: string | JSX.Element
  ) => void;
};

/**
 * Due to some issue with TypeScript when accessing static methods of an instance when you don't know
 * which class it is, we have to manually determine the class of the instance and call MyClass.staticMethod().
 * Neither instance.constructor.staticMethod() nor instance.prototype.constructor.staticMethod() work without issues.
 * See https://github.com/Microsoft/TypeScript/issues/3841#issuecomment-337560146
 */
function isListenFromDatasource(
  listen: BaseListenFormat | Listen | JSPFTrack,
  datasource: DataSourceTypes | null
) {
  if (!listen || !datasource) {
    return undefined;
  }
  if (datasource instanceof SpotifyPlayer) {
    return SpotifyPlayer.isListenFromThisService(listen);
  }
  if (datasource instanceof YoutubePlayer) {
    return YoutubePlayer.isListenFromThisService(listen);
  }
  if (datasource instanceof SoundcloudPlayer) {
    return SoundcloudPlayer.isListenFromThisService(listen);
  }
  return undefined;
}

export default function BrainzPlayer() {
  // Global App Context
  const globalAppContext = React.useContext(GlobalAppContext);
  const {
    currentUser,
    youtubeAuth,
    spotifyAuth,
    soundcloudAuth,
    APIService,
  } = globalAppContext;

  const {
    refreshSpotifyToken,
    refreshYoutubeToken,
    refreshSoundcloudToken,
    APIBaseURI: listenBrainzAPIBaseURI,
  } = APIService;

  // Constants
  // By how much should we seek in the track?
  const SEEK_TIME_MILLISECONDS = 5000;
  // Wait X milliseconds between start of song and sending a full listen
  const SUBMIT_LISTEN_AFTER_MS = 30000;
  // Check if it's time to submit the listen every X milliseconds
  const SUBMIT_LISTEN_UPDATE_INTERVAL = 5000;
  const initialWindowTitle: string = window.document.title;

  // BrainzPlayerContext
  const {
    currentListen,
    currentDataSourceIndex,
    currentTrackName,
    currentTrackArtist,
    currentTrackAlbum,
    currentTrackURL,
    playerPaused,
    isActivated,
    durationMs,
    progressMs,
    updateTime,
    listenSubmitted,
    continuousPlaybackTime,
    currentPageListens,
  } = useBrainzPlayerContext();

  const dispatch = useBrainzPlayerDispatch();

  //   React.useEffect(() => {
  //     dispatch({
  //       type: "SET_CURRENT_LISTEN",
  //       data: listens,
  //     });
  //   }, [listens]);

  // Refs
  const spotifyPlayerRef = React.useRef<SpotifyPlayer>(null);
  const youtubePlayerRef = React.useRef<YoutubePlayer>(null);
  const soundcloudPlayerRef = React.useRef<SoundcloudPlayer>(null);
  const dataSourceRefs: Array<React.RefObject<
    DataSourceTypes
  >> = React.useMemo(
    () => [spotifyPlayerRef, youtubePlayerRef, soundcloudPlayerRef],
    [spotifyPlayerRef, youtubePlayerRef, soundcloudPlayerRef]
  );
  const playerStateTimerID = React.useRef<NodeJS.Timeout | null>(null);

  // Functions
  const alertBeforeClosingPage = (event: BeforeUnloadEvent) => {
    if (!playerPaused) {
      // Some old browsers may allow to set a custom message, but this is deprecated.
      event.preventDefault();
      // eslint-disable-next-line no-param-reassign
      event.returnValue = `You are currently playing music from this page.
      Are you sure you want to close it? Playback will be stopped.`;
      return event.returnValue;
    }
    return null;
  };

  /** We use LocalStorage events as a form of communication between BrainzPlayers
   * that works across browser windows/tabs, to ensure only one BP is playing at a given time.
   * The event is not fired in the tab/window where the localStorage.setItem call initiated.
   */
  const onLocalStorageEvent = React.useCallback(
    async (event: StorageEvent) => {
      if (event.storageArea !== localStorage) return;
      if (event.key === "BrainzPlayer_stop") {
        const dataSource = dataSourceRefs[currentDataSourceIndex]?.current;
        if (dataSource && !playerPaused) {
          await dataSource.togglePlay();
        }
      }
    },
    [currentDataSourceIndex, dataSourceRefs, playerPaused]
  );

  const stopOtherBrainzPlayers = (): void => {
    // Tell all other BrainzPlayer instances to please STFU
    // Using timestamp to ensure a new value each time
    window?.localStorage?.setItem("BrainzPlayer_stop", Date.now().toString());
  };

  // Handle Notifications
  const handleError = (error: BrainzPlayerError, title: string): void => {
    if (!error) {
      return;
    }
    const message = _isString(error)
      ? error
      : `${!_isNil(error.status) ? `Error ${error.status}:` : ""} ${
          error.message || error.statusText
        }`;
    toast.error(<ToastMsg title={title} message={message} />, {
      toastId: title,
    });
  };

  const handleWarning = (
    message: string | JSX.Element,
    title: string
  ): void => {
    toast.warn(<ToastMsg title={title} message={message} />, {
      toastId: title,
    });
  };

  const handleSuccess = (
    message: string | JSX.Element,
    title: string
  ): void => {
    toast.success(<ToastMsg title={title} message={message} />, {
      toastId: title,
    });
  };

  const handleInfoMessage = (
    message: string | JSX.Element,
    title: string
  ): void => {
    toast.info(<ToastMsg title={title} message={message} />, {
      toastId: title,
    });
  };

  // Set Title
  const updateWindowTitleWithTrackName = () => {
    updateWindowTitle(currentTrackName, "🎵", ` — ${initialWindowTitle}`);
  };

  const reinitializeWindowTitle = () => {
    updateWindowTitle(initialWindowTitle);
  };

  const isCurrentlyPlaying = (element: Listen | JSPFTrack): boolean => {
    if (_isNil(currentListen)) {
      return false;
    }
    if (_has(element, "identifier")) {
      // JSPF Track format
      return (element as JSPFTrack).id === (currentListen as JSPFTrack).id;
    }
    return _isEqual(element, currentListen);
  };

  const invalidateDataSource = React.useCallback(
    (dataSource?: DataSourceTypes, message?: string | JSX.Element): void => {
      let dataSourceIndex = currentDataSourceIndex;
      if (dataSource) {
        dataSourceIndex = dataSourceRefs.findIndex(
          (source) => source.current === dataSource
        );
      }
      if (dataSourceIndex >= 0) {
        if (message) {
          handleWarning(message, "Cannot play from this source");
        }
        dataSourceRefs.splice(dataSourceIndex, 1);
      }
    },
    [currentDataSourceIndex, dataSourceRefs]
  );

  const getListenMetadataToSubmit = (): BaseListenFormat => {
    const dataSource = dataSourceRefs[currentDataSourceIndex];

    const brainzplayer_metadata = {
      artist_name: currentTrackArtist,
      release_name: currentTrackAlbum,
      track_name: currentTrackName,
    };
    // Create a new listen and augment it with the existing listen and datasource's metadata
    const newListen: BaseListenFormat = {
      // convert Javascript millisecond time to unix epoch in seconds
      listened_at: Math.floor(Date.now() / 1000),
      track_metadata:
        cloneDeep((currentListen as BaseListenFormat)?.track_metadata) ?? {},
    };

    const musicServiceName = dataSource.current?.name;
    let musicServiceDomain = dataSource.current?.domainName;
    // Best effort try?
    if (!musicServiceDomain && currentTrackURL) {
      try {
        // Browser could potentially be missing the URL constructor
        musicServiceDomain = new URL(currentTrackURL).hostname;
      } catch (e) {
        // Do nothing, we just fallback gracefully to dataSource name.
      }
    }

    // ensure the track_metadata.additional_info path exists and add brainzplayer_metadata field
    assign(newListen.track_metadata, {
      brainzplayer_metadata,
      additional_info: {
        duration_ms: durationMs > 0 ? durationMs : undefined,
        media_player: "BrainzPlayer",
        submission_client: "BrainzPlayer",
        // TODO:  passs the GIT_COMMIT_SHA env variable to the globalprops and add it here as submission_client_version
        // submission_client_version:"",
        music_service: musicServiceDomain,
        music_service_name: musicServiceName,
        origin_url: currentTrackURL,
      },
    });
    return newListen;
  };

  const submitListenToListenBrainz = async (
    listenType: ListenType,
    listen: BaseListenFormat,
    retries: number = 3
  ): Promise<void> => {
    const dataSource = dataSourceRefs[currentDataSourceIndex];
    if (!currentUser || !currentUser.auth_token) {
      return;
    }
    const isPlayingNowType = listenType === "playing_now";
    // Always submit playing_now listens for a better experience on LB pages
    // (ingestion of playing-now info from spotify can take minutes,
    // sometimes not getting updated before the end of the track)
    if (
      isPlayingNowType ||
      (dataSource?.current && !dataSource.current.datasourceRecordsListens())
    ) {
      try {
        const { auth_token } = currentUser;
        let processedPayload = listen;
        // When submitting playing_now listens, listened_at must NOT be present
        if (isPlayingNowType) {
          processedPayload = omit(listen, "listened_at") as Listen;
        }

        const struct = {
          listen_type: listenType,
          payload: [processedPayload],
        } as SubmitListensPayload;
        const url = `${listenBrainzAPIBaseURI}/submit-listens`;

        const response = await fetch(url, {
          method: "POST",
          headers: {
            Authorization: `Token ${auth_token}`,
            "Content-Type": "application/json;charset=UTF-8",
          },
          body: JSON.stringify(struct),
        });
        if (!response.ok) {
          throw response.statusText;
        }
      } catch (error) {
        if (retries > 0) {
          // Something went wrong, try again in 3 seconds.
          await new Promise((resolve) => {
            setTimeout(resolve, 3000);
          });
          await submitListenToListenBrainz(listenType, listen, retries - 1);
        } else if (!isPlayingNowType) {
          handleWarning(error.toString(), "Could not save this listen");
        }
      }
    }
  };

  const checkProgressAndSubmitListen = async () => {
    if (!currentUser?.auth_token || listenSubmitted) {
      return;
    }
    let playbackTimeRequired = SUBMIT_LISTEN_AFTER_MS;
    if (durationMs > 0) {
      playbackTimeRequired = Math.min(
        SUBMIT_LISTEN_AFTER_MS,
        durationMs - SUBMIT_LISTEN_UPDATE_INTERVAL
      );
    }
    if (continuousPlaybackTime >= playbackTimeRequired) {
      const listen = getListenMetadataToSubmit();
      await submitListenToListenBrainz("single", listen);
    }
  };

  // eslint-disable-next-line react/sort-comp
  const debouncedCheckProgressAndSubmitListen = debounce(
    checkProgressAndSubmitListen,
    SUBMIT_LISTEN_UPDATE_INTERVAL,
    {
      leading: false,
      trailing: true,
      maxWait: SUBMIT_LISTEN_UPDATE_INTERVAL,
    }
  );

  const playListen = React.useCallback(
    (listen: Listen | JSPFTrack, datasourceIndex: number = 0): void => {
      dispatch({
        currentListen: listen,
        isActivated: true,
        listenSubmitted: false,
        continuousPlaybackTime: 0,
      });

      window.postMessage(
        { brainzplayer_event: "current-listen-change", payload: listen },
        window.location.origin
      );

      let selectedDatasourceIndex: number;
      if (datasourceIndex === 0) {
        /** If available, retrieve the service the listen was listened with */
        const listenedFromIndex = dataSourceRefs.findIndex((datasourceRef) => {
          const { current } = datasourceRef;
          return isListenFromDatasource(listen, current);
        });
        selectedDatasourceIndex =
          listenedFromIndex === -1 ? 0 : listenedFromIndex;
      } else {
        /** If no matching datasource was found, revert to the default bahaviour
         * (try playing from source 0 or try next source)
         */
        selectedDatasourceIndex = datasourceIndex;
      }

      const datasource = dataSourceRefs[selectedDatasourceIndex]?.current;
      if (!datasource) {
        return;
      }
      // Check if we can play the listen with the selected datasource
      // otherwise skip to the next datasource without trying or setting currentDataSourceIndex
      // This prevents rendering datasource iframes when we can't use the datasource
      if (
        !isListenFromDatasource(listen, datasource) &&
        !datasource.canSearchAndPlayTracks()
      ) {
        playListen(listen, datasourceIndex + 1);
        return;
      }
      stopOtherBrainzPlayers();
      dispatch({ currentDataSourceIndex: selectedDatasourceIndex }, () => {
        datasource.playListen(listen);
      });
    },
    [dataSourceRefs, dispatch]
  );

  const playNextTrack = (invert: boolean = false): void => {
    if (!isActivated) {
      // Player has not been activated by the user, do nothing.
      return;
    }
    debouncedCheckProgressAndSubmitListen.flush();

    if (currentPageListens.length === 0) {
      handleWarning(
        "You can try loading listens or refreshing the page",
        "No listens to play"
      );
      return;
    }

    const currentListenIndex = currentPageListens.findIndex(isCurrentlyPlaying);

    let nextListenIndex;
    if (currentListenIndex === -1) {
      // No current listen index found, default to first item
      nextListenIndex = 0;
    } else if (invert === true) {
      // Invert means "play previous track" instead of next track
      // `|| 0` constrains to positive numbers
      nextListenIndex = currentListenIndex - 1 || 0;
    } else {
      nextListenIndex = currentListenIndex + 1;
    }

    const nextListen = currentPageListens[nextListenIndex];
    if (!nextListen) {
      handleWarning(
        "You can try loading more listens or refreshing the page",
        "No more listens to play"
      );
      reinitializeWindowTitle();
      return;
    }
    playListen(nextListen);
  };

  const playPreviousTrack = (): void => {
    playNextTrack(true);
  };

  const progressChange = (newProgressMs: number): void => {
    dispatch({ progressMs: newProgressMs, updateTime: performance.now() });
  };

  const seekToPositionMs = (msTimecode: number): void => {
    if (!isActivated) {
      // Player has not been activated by the user, do nothing.
      return;
    }
    const dataSource = dataSourceRefs[currentDataSourceIndex]?.current;
    if (!dataSource) {
      invalidateDataSource();
      return;
    }
    dataSource.seekToPositionMs(msTimecode);
    progressChange(msTimecode);
  };

  const seekForward = (): void => {
    seekToPositionMs(progressMs + SEEK_TIME_MILLISECONDS);
  };

  const seekBackward = (): void => {
    seekToPositionMs(progressMs - SEEK_TIME_MILLISECONDS);
  };

  const mediaSessionHandlers = [
    { action: "previoustrack", handler: playPreviousTrack },
    { action: "nexttrack", handler: playNextTrack },
    { action: "seekbackward", handler: seekBackward },
    { action: "seekforward", handler: seekForward },
  ];

  const activatePlayerAndPlay = (): void => {
    overwriteMediaSession(mediaSessionHandlers);
    dispatch({ isActivated: true }, () => {
      playNextTrack();
    });
  };

  const togglePlay = React.useCallback(async (): Promise<void> => {
    try {
      const dataSource = dataSourceRefs[currentDataSourceIndex]?.current;
      if (!dataSource) {
        invalidateDataSource();
        return;
      }
      if (playerPaused) {
        stopOtherBrainzPlayers();
      }
      await dataSource.togglePlay();
    } catch (error) {
      handleError(error, "Could not play");
    }
  }, [currentDataSourceIndex, dataSourceRefs, invalidateDataSource]);

  const getCurrentTrackName = (): string => {
    return getTrackName(currentListen);
  };

  const getCurrentTrackArtists = (): string | undefined => {
    return getArtistName(currentListen);
  };

  const stopPlayerStateTimer = React.useCallback((): void => {
    debouncedCheckProgressAndSubmitListen.flush();
    if (playerStateTimerID.current) {
      clearInterval(playerStateTimerID.current);
    }
    playerStateTimerID.current = null;
  }, [debouncedCheckProgressAndSubmitListen]);

  /* Updating the progress bar without calling any API to check current player state */
  const getStatePosition = (): void => {
    let newProgressMs: number;
    let elapsedTimeSinceLastUpdate: number;
    if (playerPaused) {
      newProgressMs = progressMs || 0;
      elapsedTimeSinceLastUpdate = 0;
    } else {
      elapsedTimeSinceLastUpdate = performance.now() - updateTime;
      const position = progressMs + elapsedTimeSinceLastUpdate;
      newProgressMs = position > durationMs ? durationMs : position;
    }
    dispatch({
      progressMs: newProgressMs,
      updateTime: performance.now(),
      continuousPlaybackTime:
        continuousPlaybackTime + elapsedTimeSinceLastUpdate,
    });
  };

  const startPlayerStateTimer = (): void => {
    stopPlayerStateTimer();
    playerStateTimerID.current = setInterval(() => {
      getStatePosition();
      debouncedCheckProgressAndSubmitListen();
    }, 400);
  };

  /* Listeners for datasource events */
  const failedToPlayTrack = (): void => {
    if (!isActivated) {
      // Player has not been activated by the user, do nothing.
      return;
    }

    if (currentListen && currentDataSourceIndex < dataSourceRefs.length - 1) {
      // Try playing the listen with the next dataSource
      playListen(currentListen, currentDataSourceIndex + 1);
    } else {
      stopPlayerStateTimer();
      playNextTrack();
    }
  };

  const playerPauseChange = (paused: boolean): void => {
    dispatch({ playerPaused: paused }, () => {
      if (paused) {
        stopPlayerStateTimer();
        reinitializeWindowTitle();
      } else {
        startPlayerStateTimer();
        updateWindowTitleWithTrackName();
      }
    });
    if (hasMediaSessionSupport()) {
      window.navigator.mediaSession.playbackState = paused
        ? "paused"
        : "playing";
    }
  };

  const durationChange = (newDurationMs: number): void => {
    dispatch({ durationMs: newDurationMs }, () => {
      startPlayerStateTimer();
    });
  };

  const submitNowPlayingToListenBrainz = async (): Promise<void> => {
    const newListen = getListenMetadataToSubmit();
    return submitListenToListenBrainz("playing_now", newListen);
  };

  const trackInfoChange = (
    title: string,
    trackURL: string,
    artist?: string,
    album?: string,
    artwork?: Array<MediaImage>
  ): void => {
    dispatch(
      {
        currentTrackName: title,
        currentTrackArtist: artist!,
        currentTrackAlbum: album,
        currentTrackURL: trackURL,
      },
      () => {
        updateWindowTitleWithTrackName();
      }
    );
    if (playerPaused) {
      // Don't send notifications or any of that if the player is not playing
      // (Avoids getting notifications upon pausing a track)
      return;
    }

    if (hasMediaSessionSupport()) {
      overwriteMediaSession(mediaSessionHandlers);
      updateMediaSession(title, artist, album, artwork);
    }
    // Send a notification. If user allowed browser/OS notifications use that,
    // otherwise show a toast notification on the page
    hasNotificationPermission().then((permissionGranted) => {
      if (permissionGranted) {
        createNotification(title, artist, album, artwork?.[0]?.src);
      } else {
        const message = (
          <div className="alert brainzplayer-alert">
            {artwork?.length ? (
              <img
                className="alert-thumbnail"
                src={artwork[0].src}
                alt={album || title}
              />
            ) : (
              <FontAwesomeIcon icon={faPlayCircle as IconProp} />
            )}
            <div>
              {title}
              {artist && ` — ${artist}`}
              {album && ` — ${album}`}
            </div>
          </div>
        );
        handleInfoMessage(message, `Playing a track`);
      }
    });

    submitNowPlayingToListenBrainz();
  };

  // eslint-disable-next-line react/sort-comp
  const throttledTrackInfoChange = _throttle(trackInfoChange, 2000, {
    leading: false,
    trailing: true,
  });

  const receiveBrainzPlayerMessage = React.useCallback(
    (event: MessageEvent) => {
      if (event.origin !== window.location.origin) {
        // Received postMessage from different origin, ignoring it
        return;
      }
      const { brainzplayer_event, payload } = event.data;
      switch (brainzplayer_event) {
        case "play-listen":
          playListen(payload);
          break;
        case "force-play":
          togglePlay();
          break;
        default:
        // do nothing
      }
    },
    [playListen, togglePlay]
  );

  React.useEffect(() => {
    window.addEventListener("storage", onLocalStorageEvent);
    window.addEventListener("message", receiveBrainzPlayerMessage);
    window.addEventListener("beforeunload", alertBeforeClosingPage);
    // Remove SpotifyPlayer if the user doesn't have the relevant permissions to use it
    if (
      !SpotifyPlayer.hasPermissions(spotifyAuth) &&
      spotifyPlayerRef?.current
    ) {
      invalidateDataSource(spotifyPlayerRef.current);
    }
    if (
      !SoundcloudPlayer.hasPermissions(soundcloudAuth) &&
      soundcloudPlayerRef?.current
    ) {
      invalidateDataSource(soundcloudPlayerRef.current);
    }
    return () => {
      window.removeEventListener("storage", onLocalStorageEvent);
      window.removeEventListener("message", receiveBrainzPlayerMessage);
      window.removeEventListener("beforeunload", alertBeforeClosingPage);
      stopPlayerStateTimer();
    };
  }, []);

  return (
    <div>
      <BrainzPlayerUI
        playPreviousTrack={playPreviousTrack}
        playNextTrack={playNextTrack}
        togglePlay={isActivated ? togglePlay : activatePlayerAndPlay}
        playerPaused={playerPaused}
        trackName={currentTrackName}
        artistName={currentTrackArtist}
        progressMs={progressMs}
        durationMs={durationMs}
        seekToPositionMs={seekToPositionMs}
        listenBrainzAPIBaseURI={listenBrainzAPIBaseURI}
        currentListen={currentListen}
        trackUrl={currentTrackURL}
        currentDataSourceIcon={
          dataSourceRefs[currentDataSourceIndex]?.current?.icon
        }
        currentDataSourceName={
          dataSourceRefs[currentDataSourceIndex]?.current?.name
        }
      >
        <SpotifyPlayer
          show={
            isActivated &&
            dataSourceRefs[currentDataSourceIndex]?.current instanceof
              SpotifyPlayer
          }
          refreshSpotifyToken={refreshSpotifyToken}
          onInvalidateDataSource={invalidateDataSource}
          ref={spotifyPlayerRef}
          spotifyUser={spotifyAuth}
          playerPaused={playerPaused}
          onPlayerPausedChange={playerPauseChange}
          onProgressChange={progressChange}
          onDurationChange={durationChange}
          onTrackInfoChange={throttledTrackInfoChange}
          onTrackEnd={playNextTrack}
          onTrackNotFound={failedToPlayTrack}
          handleError={handleError}
          handleWarning={handleWarning}
          handleSuccess={handleSuccess}
        />
        <YoutubePlayer
          show={
            isActivated &&
            dataSourceRefs[currentDataSourceIndex]?.current instanceof
              YoutubePlayer
          }
          onInvalidateDataSource={invalidateDataSource}
          ref={youtubePlayerRef}
          youtubeUser={youtubeAuth}
          refreshYoutubeToken={refreshYoutubeToken}
          playerPaused={playerPaused}
          onPlayerPausedChange={playerPauseChange}
          onProgressChange={progressChange}
          onDurationChange={durationChange}
          onTrackInfoChange={throttledTrackInfoChange}
          onTrackEnd={playNextTrack}
          onTrackNotFound={failedToPlayTrack}
          handleError={handleError}
          handleWarning={handleWarning}
          handleSuccess={handleSuccess}
        />
        <SoundcloudPlayer
          show={
            isActivated &&
            dataSourceRefs[currentDataSourceIndex]?.current instanceof
              SoundcloudPlayer
          }
          onInvalidateDataSource={invalidateDataSource}
          ref={soundcloudPlayerRef}
          soundcloudUser={soundcloudAuth}
          refreshSoundcloudToken={refreshSoundcloudToken}
          playerPaused={playerPaused}
          onPlayerPausedChange={playerPauseChange}
          onProgressChange={progressChange}
          onDurationChange={durationChange}
          onTrackInfoChange={throttledTrackInfoChange}
          onTrackEnd={playNextTrack}
          onTrackNotFound={failedToPlayTrack}
          handleError={handleError}
          handleWarning={handleWarning}
          handleSuccess={handleSuccess}
        />
      </BrainzPlayerUI>
    </div>
  );
}
