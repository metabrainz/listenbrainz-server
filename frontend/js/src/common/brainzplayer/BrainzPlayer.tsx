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
import { Link, useLocation } from "react-router-dom";
import { Helmet } from "react-helmet";
import {
  ToastMsg,
  createNotification,
  hasMediaSessionSupport,
  hasNotificationPermission,
  overwriteMediaSession,
  updateMediaSession,
} from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import BrainzPlayerUI from "./BrainzPlayerUI";
import SoundcloudPlayer from "./SoundcloudPlayer";
import SpotifyPlayer from "./SpotifyPlayer";
import YoutubePlayer from "./YoutubePlayer";
import AppleMusicPlayer from "./AppleMusicPlayer";
import {
  DataSourceKey,
  defaultDataSourcesPriority,
} from "../../settings/brainzplayer/BrainzPlayerSettings";
import {
  QueueRepeatModes,
  useBrainzPlayerContext,
  useBrainzPlayerDispatch,
} from "./BrainzPlayerContext";

export type DataSourceType = {
  name: string;
  icon: IconProp;
  iconColor: string;
  playListen: (listen: Listen | JSPFTrack) => void;
  togglePlay: () => void;
  seekToPositionMs: (msTimecode: number) => void;
  canSearchAndPlayTracks: () => boolean;
  datasourceRecordsListens: () => boolean;
};

export type DataSourceTypes =
  | SpotifyPlayer
  | YoutubePlayer
  | SoundcloudPlayer
  | AppleMusicPlayer;

export type DataSourceProps = {
  show: boolean;
  volume?: number;
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
  if (datasource instanceof AppleMusicPlayer) {
    return AppleMusicPlayer.isListenFromThisService(listen);
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
    appleAuth,
    userPreferences,
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

  const brainzPlayerDisabled =
    userPreferences?.brainzplayer?.brainzplayerEnabled === false ||
    (userPreferences?.brainzplayer?.spotifyEnabled === false &&
      userPreferences?.brainzplayer?.youtubeEnabled === false &&
      userPreferences?.brainzplayer?.soundcloudEnabled === false &&
      userPreferences?.brainzplayer?.appleMusicEnabled === false);

  // BrainzPlayerContext
  const brainzPlayerContext = useBrainzPlayerContext();

  const brainzPlayerContextRef = React.useRef(brainzPlayerContext);
  brainzPlayerContextRef.current = brainzPlayerContext;

  const dispatch = useBrainzPlayerDispatch();

  // State
  const [htmlTitle, setHtmlTitle] = React.useState<string>(
    window.document.title
  );
  const [currentHTMLTitle, setCurrentHTMLTitle] = React.useState<string | null>(
    null
  );

  const {
    spotifyEnabled = true,
    appleMusicEnabled = true,
    soundcloudEnabled = true,
    youtubeEnabled = true,
    brainzplayerEnabled = true,
    dataSourcesPriority = defaultDataSourcesPriority,
  } = userPreferences?.brainzplayer ?? {};

  const enabledDataSources = [
    spotifyEnabled && SpotifyPlayer.hasPermissions(spotifyAuth) && "spotify",
    appleMusicEnabled &&
      AppleMusicPlayer.hasPermissions(appleAuth) &&
      "appleMusic",
    soundcloudEnabled &&
      SoundcloudPlayer.hasPermissions(soundcloudAuth) &&
      "soundcloud",
    youtubeEnabled && "youtube",
  ].filter(Boolean) as Array<DataSourceKey>;

  const sortedDataSources = dataSourcesPriority.filter((key) =>
    enabledDataSources.includes(key)
  );

  // Refs
  const spotifyPlayerRef = React.useRef<SpotifyPlayer>(null);
  const youtubePlayerRef = React.useRef<YoutubePlayer>(null);
  const soundcloudPlayerRef = React.useRef<SoundcloudPlayer>(null);
  const appleMusicPlayerRef = React.useRef<AppleMusicPlayer>(null);
  const dataSourceRefs: Array<React.RefObject<
    DataSourceTypes
  >> = React.useMemo(() => {
    const dataSources: Array<React.RefObject<DataSourceTypes>> = [];
    sortedDataSources.forEach((key) => {
      switch (key) {
        case "spotify":
          dataSources.push(spotifyPlayerRef);
          break;
        case "youtube":
          dataSources.push(youtubePlayerRef);
          break;
        case "soundcloud":
          dataSources.push(soundcloudPlayerRef);
          break;
        case "appleMusic":
          dataSources.push(appleMusicPlayerRef);
          break;
        default:
        // do nothing
      }
    });
    return dataSources;
  }, [sortedDataSources]);

  const playerStateTimerID = React.useRef<NodeJS.Timeout | null>(null);

  // Functions
  const alertBeforeClosingPage = (event: BeforeUnloadEvent) => {
    if (!brainzPlayerContextRef.current.playerPaused) {
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
  const onLocalStorageEvent = async (event: StorageEvent) => {
    if (event.storageArea !== localStorage) return;
    if (event.key === "BrainzPlayer_stop") {
      const dataSource =
        dataSourceRefs[brainzPlayerContextRef.current.currentDataSourceIndex]
          ?.current;
      if (dataSource && !brainzPlayerContextRef.current.playerPaused) {
        await dataSource.togglePlay();
      }
    }
  };

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
    const trackName = brainzPlayerContextRef.current.currentTrackName || "";
    setCurrentHTMLTitle(`🎵 ${trackName}`);
  };

  const reinitializeWindowTitle = () => {
    setCurrentHTMLTitle(htmlTitle);
  };

  const invalidateDataSource = (
    dataSource?: DataSourceTypes,
    message?: string | JSX.Element
  ): void => {
    let dataSourceIndex = brainzPlayerContextRef.current.currentDataSourceIndex;
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
  };

  const getListenMetadataToSubmit = (): BaseListenFormat => {
    const dataSource =
      dataSourceRefs[brainzPlayerContextRef.current.currentDataSourceIndex];

    const brainzplayer_metadata = {
      artist_name: brainzPlayerContextRef.current.currentTrackArtist,
      release_name: brainzPlayerContextRef.current.currentTrackAlbum,
      track_name: brainzPlayerContextRef.current.currentTrackName,
    };
    // Create a new listen and augment it with the existing listen and datasource's metadata
    const newListen: BaseListenFormat = {
      // convert Javascript millisecond time to unix epoch in seconds
      listened_at: Math.floor(Date.now() / 1000),
      track_metadata:
        cloneDeep(
          (brainzPlayerContextRef.current.currentListen as BaseListenFormat)
            ?.track_metadata
        ) ?? {},
    };

    const musicServiceName = dataSource.current?.name;
    let musicServiceDomain = dataSource.current?.domainName;
    // Best effort try?
    if (!musicServiceDomain && brainzPlayerContextRef.current.currentTrackURL) {
      try {
        // Browser could potentially be missing the URL constructor
        musicServiceDomain = new URL(
          brainzPlayerContextRef.current.currentTrackURL
        ).hostname;
      } catch (e) {
        // Do nothing, we just fallback gracefully to dataSource name.
      }
    }

    // ensure the track_metadata.additional_info path exists and add brainzplayer_metadata field
    assign(newListen.track_metadata, {
      brainzplayer_metadata,
      additional_info: {
        duration_ms:
          brainzPlayerContextRef.current.durationMs > 0
            ? brainzPlayerContextRef.current.durationMs
            : undefined,
        media_player: "BrainzPlayer",
        submission_client: "BrainzPlayer",
        // TODO:  passs the GIT_COMMIT_SHA env variable to the globalprops and add it here as submission_client_version
        // submission_client_version:"",
        music_service: musicServiceDomain,
        music_service_name: musicServiceName,
        origin_url: brainzPlayerContextRef.current.currentTrackURL,
      },
    });
    return newListen;
  };

  const submitListenToListenBrainz = async (
    listenType: ListenType,
    listen: BaseListenFormat,
    retries: number = 3
  ): Promise<void> => {
    const dataSource =
      dataSourceRefs[brainzPlayerContextRef.current.currentDataSourceIndex];
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
    if (
      !currentUser?.auth_token ||
      brainzPlayerContextRef.current.listenSubmitted
    ) {
      return;
    }
    let playbackTimeRequired = SUBMIT_LISTEN_AFTER_MS;
    if (brainzPlayerContextRef.current.durationMs > 0) {
      playbackTimeRequired = Math.min(
        SUBMIT_LISTEN_AFTER_MS,
        brainzPlayerContextRef.current.durationMs -
          SUBMIT_LISTEN_UPDATE_INTERVAL
      );
    }
    if (
      brainzPlayerContextRef.current.continuousPlaybackTime >=
      playbackTimeRequired
    ) {
      const listen = getListenMetadataToSubmit();
      dispatch({ listenSubmitted: true });
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

  const playListen = async (
    listen: BrainzPlayerQueueItem,
    nextListenIndex: number,
    datasourceIndex: number = 0
  ): Promise<void> => {
    dispatch({
      currentListen: listen,
      currentListenIndex: nextListenIndex,
      isActivated: true,
      listenSubmitted: false,
      continuousPlaybackTime: 0,
    });

    window.postMessage(
      {
        brainzplayer_event: "current-listen-change",
        payload: omit(listen, "id"),
      },
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
      playListen(listen, nextListenIndex, datasourceIndex + 1);
      return;
    }
    stopOtherBrainzPlayers();
    dispatch({ currentDataSourceIndex: selectedDatasourceIndex }, async () => {
      while (
        brainzPlayerContextRef.current.currentListen !== listen ||
        brainzPlayerContextRef.current.currentDataSourceIndex !==
          selectedDatasourceIndex
      ) {
        // eslint-disable-next-line no-await-in-loop, no-promise-executor-return
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
      datasource.playListen(listen);
    });
  };

  const stopPlayerStateTimer = (): void => {
    debouncedCheckProgressAndSubmitListen.flush();
    if (playerStateTimerID.current) {
      clearInterval(playerStateTimerID.current);
    }
    playerStateTimerID.current = null;
  };

  const playNextTrack = (invert: boolean = false): void => {
    if (!brainzPlayerContextRef.current.isActivated) {
      // Player has not been activated by the user, do nothing.
      return;
    }
    debouncedCheckProgressAndSubmitListen.flush();

    const currentQueue = brainzPlayerContextRef.current.queue;
    const currentAmbientQueue = brainzPlayerContextRef.current.ambientQueue;

    if (currentQueue.length === 0 && currentAmbientQueue.length === 0) {
      handleWarning(
        "You can try loading listens or refreshing the page",
        "No listens to play"
      );
      return;
    }

    const currentPlayingListenIndex =
      brainzPlayerContextRef.current.currentListenIndex;

    let nextListenIndex: number;
    // If the queue repeat mode is one, then play the same track again
    if (
      brainzPlayerContextRef.current.queueRepeatMode === QueueRepeatModes.one
    ) {
      nextListenIndex =
        currentPlayingListenIndex + (currentPlayingListenIndex < 0 ? 1 : 0);
    } else {
      // Otherwise, play the next track in the queue
      nextListenIndex = currentPlayingListenIndex + (invert === true ? -1 : 1);
    }

    // If nextListenIndex is less than 0, wrap around to the last track in the queue
    if (nextListenIndex < 0) {
      nextListenIndex = currentQueue.length - 1;
    }

    // If nextListenIndex is within the queue length, play the next track
    if (nextListenIndex < currentQueue.length) {
      const nextListen = currentQueue[nextListenIndex];
      playListen(nextListen, nextListenIndex, 0);
      return;
    }

    // If the nextListenIndex is greater than the queue length, i.e. the queue has ended, then there are three possibilities:
    // 1. If there are listens in the ambient queue, then play the first listen in the ambient queue.
    //    In this case, we'll move the first listen from the ambient queue to the main queue and play it.
    // 2. If there are no listens in the ambient queue, then play the first listen in the main queue.
    if (currentAmbientQueue.length > 0) {
      const ambientQueueTop = currentAmbientQueue.shift();
      if (ambientQueueTop) {
        const currentQueueLength = currentQueue.length;
        dispatch(
          {
            type: "ADD_LISTEN_TO_BOTTOM_OF_QUEUE",
            data: ambientQueueTop,
          },
          async () => {
            while (
              brainzPlayerContextRef.current.queue.length !==
              currentQueueLength + 1
            ) {
              // eslint-disable-next-line no-await-in-loop, no-promise-executor-return
              await new Promise((resolve) => setTimeout(resolve, 100));
            }
            const nextListen =
              brainzPlayerContextRef.current.queue[currentQueueLength];
            dispatch({ ambientQueue: currentAmbientQueue });
            playListen(nextListen, currentQueueLength, 0);
          }
        );
        return;
      }
    } else if (
      brainzPlayerContextRef.current.queueRepeatMode === QueueRepeatModes.off
    ) {
      // 3. If there are no listens in the ambient queue and the queue repeat mode is off, then stop the player
      stopPlayerStateTimer();
      reinitializeWindowTitle();
      return;
    }

    // If there are no listens in the ambient queue, then play the first listen in the main queue
    nextListenIndex = 0;
    const nextListen = currentQueue[nextListenIndex];
    if (!nextListen) {
      handleWarning(
        "You can try loading listens or refreshing the page",
        "No listens to play"
      );
      return;
    }
    playListen(nextListen, nextListenIndex, 0);
  };

  const playPreviousTrack = (): void => {
    playNextTrack(true);
  };

  const progressChange = (newProgressMs: number): void => {
    dispatch({ progressMs: newProgressMs, updateTime: performance.now() });
  };

  const seekToPositionMs = (msTimecode: number): void => {
    if (!brainzPlayerContextRef.current.isActivated) {
      // Player has not been activated by the user, do nothing.
      return;
    }
    const dataSource =
      dataSourceRefs[brainzPlayerContextRef.current.currentDataSourceIndex]
        ?.current;
    if (!dataSource) {
      invalidateDataSource();
      return;
    }
    dataSource.seekToPositionMs(msTimecode);
    progressChange(msTimecode);
  };

  const seekForward = (): void => {
    seekToPositionMs(
      brainzPlayerContextRef.current.progressMs + SEEK_TIME_MILLISECONDS
    );
  };

  const seekBackward = (): void => {
    seekToPositionMs(
      brainzPlayerContextRef.current.progressMs - SEEK_TIME_MILLISECONDS
    );
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

  const togglePlay = async (): Promise<void> => {
    try {
      const dataSource =
        dataSourceRefs[brainzPlayerContextRef.current.currentDataSourceIndex]
          ?.current;
      if (!dataSource) {
        invalidateDataSource();
        return;
      }
      if (brainzPlayerContextRef.current.playerPaused) {
        stopOtherBrainzPlayers();
      }
      await dataSource.togglePlay();
    } catch (error) {
      handleError(error, "Could not play");
    }
  };

  /* Updating the progress bar without calling any API to check current player state */
  const updatePlayerProgressBar = (): void => {
    dispatch({ type: "SET_PLAYBACK_TIMER" });
  };

  const startPlayerStateTimer = (): void => {
    stopPlayerStateTimer();
    playerStateTimerID.current = setInterval(() => {
      updatePlayerProgressBar();
      debouncedCheckProgressAndSubmitListen();
    }, 400);
  };

  /* Listeners for datasource events */
  const failedToPlayTrack = (): void => {
    if (!brainzPlayerContextRef.current.isActivated) {
      // Player has not been activated by the user, do nothing.
      return;
    }

    if (
      brainzPlayerContextRef.current.currentListen &&
      brainzPlayerContextRef.current.currentDataSourceIndex <
        dataSourceRefs.length - 1
    ) {
      // Try playing the listen with the next dataSource
      playListen(
        brainzPlayerContextRef.current.currentListen,
        brainzPlayerContextRef.current.currentListenIndex,
        brainzPlayerContextRef.current.currentDataSourceIndex + 1
      );
    } else {
      handleWarning(
        <>
          We tried searching for this track on the music services you are
          connected to, but did not find a match to play.
          <br />
          To enable more music services please go to the{" "}
          <Link to="/settings/brainzplayer/">music player preferences.</Link>
        </>,
        "Could not find a match"
      );
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
        currentTrackCoverURL: artwork?.[0]?.src,
      },
      () => {
        updateWindowTitleWithTrackName();
        if (!brainzPlayerContextRef.current.playerPaused) {
          submitNowPlayingToListenBrainz();
        }
      }
    );
    if (brainzPlayerContextRef.current.playerPaused) {
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
  };

  const clearQueue = async (): Promise<void> => {
    const currentQueue = brainzPlayerContextRef.current.queue;

    // Clear the queue by keeping only the currently playing song
    const currentPlayingListenIndex =
      brainzPlayerContextRef.current.currentListenIndex;
    dispatch({
      queue: currentQueue[currentPlayingListenIndex]
        ? [currentQueue[currentPlayingListenIndex]]
        : [],
    });
  };

  const playNextListenFromQueue = (datasourceIndex: number = 0): void => {
    const currentPlayingListenIndex =
      brainzPlayerContextRef.current.currentListenIndex;
    const nextTrack =
      brainzPlayerContextRef.current.queue[currentPlayingListenIndex + 1];
    playListen(nextTrack, currentPlayingListenIndex + 1, datasourceIndex);
  };

  const playListenEventHandler = (listen: Listen | JSPFTrack) => {
    dispatch(
      {
        type: "ADD_LISTEN_TO_TOP_OF_QUEUE",
        data: listen,
      },
      () => {
        playNextListenFromQueue();
      }
    );
  };

  const playAmbientQueue = (tracks: BrainzPlayerQueue): void => {
    // 1. Clear the items in the queue after the current playing track
    const currentPlayingListenIndex =
      brainzPlayerContextRef.current.currentListenIndex;
    dispatch(
      {
        type: "CLEAR_QUEUE_AFTER_CURRENT_AND_SET_AMBIENT_QUEUE",
        data: tracks,
        isActivated: true,
      },
      async () => {
        while (
          brainzPlayerContextRef.current.queue.length !==
            currentPlayingListenIndex + 1 &&
          brainzPlayerContextRef.current.isActivated
        ) {
          // eslint-disable-next-line no-await-in-loop, no-promise-executor-return
          await new Promise((resolve) => setTimeout(resolve, 100));
        }

        // 2. Play the first item in the ambient queue
        playNextTrack();
      }
    );
  };

  // eslint-disable-next-line react/sort-comp
  const throttledTrackInfoChange = _throttle(trackInfoChange, 2000, {
    leading: false,
    trailing: true,
  });

  const receiveBrainzPlayerMessage = (event: MessageEvent) => {
    if (event.origin !== window.location.origin) {
      // Received postMessage from different origin, ignoring it
      return;
    }
    const { brainzplayer_event, payload } = event.data;
    if (!brainzplayer_event) {
      return;
    }
    if (userPreferences?.brainzplayer) {
      if (brainzPlayerDisabled) {
        toast.info(
          <ToastMsg
            title="BrainzPlayer disabled"
            message={
              <>
                You have disabled all music services for playback on
                ListenBrainz. To enable them again, please go to the{" "}
                <Link to="/settings/brainzplayer/">
                  music player preferences
                </Link>{" "}
                page
              </>
            }
          />
        );
        return;
      }
    }
    switch (brainzplayer_event) {
      case "play-listen":
        playListenEventHandler(payload);
        break;
      case "force-play":
        togglePlay();
        break;
      case "play-ambient-queue":
        playAmbientQueue(payload);
        break;
      default:
      // do nothing
    }
  };

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spotifyAuth, soundcloudAuth]);

  const { pathname } = useLocation();

  // Hide the player if user is on homepage and the player is not activated, and there are nothing in both the queue
  if (
    pathname === "/" &&
    !brainzPlayerContextRef.current.isActivated &&
    brainzPlayerContextRef.current.queue.length === 0 &&
    brainzPlayerContextRef.current.ambientQueue.length === 0
  ) {
    return null;
  }

  return (
    <div
      data-testid="brainzplayer"
      className={!brainzplayerEnabled ? "hidden" : ""}
    >
      {!brainzPlayerContextRef.current.playerPaused && (
        <Helmet
          key={htmlTitle}
          onChangeClientState={(newState) => {
            if (newState.title && !newState.title.includes("🎵")) {
              setHtmlTitle(newState.title?.replace(" - ListenBrainz", ""));
            }
          }}
        >
          <title>{currentHTMLTitle}</title>
        </Helmet>
      )}
      <BrainzPlayerUI
        disabled={brainzPlayerDisabled}
        playPreviousTrack={playPreviousTrack}
        playNextTrack={playNextTrack}
        togglePlay={
          brainzPlayerContextRef.current.isActivated
            ? togglePlay
            : activatePlayerAndPlay
        }
        seekToPositionMs={seekToPositionMs}
        listenBrainzAPIBaseURI={listenBrainzAPIBaseURI}
        currentDataSource={
          dataSourceRefs[brainzPlayerContextRef.current.currentDataSourceIndex]
            ?.current
        }
        clearQueue={clearQueue}
      >
        {userPreferences?.brainzplayer?.spotifyEnabled !== false && (
          <SpotifyPlayer
            volume={brainzPlayerContextRef.current.volume}
            show={
              brainzPlayerContextRef.current.isActivated &&
              dataSourceRefs[
                brainzPlayerContextRef.current.currentDataSourceIndex
              ]?.current instanceof SpotifyPlayer
            }
            refreshSpotifyToken={refreshSpotifyToken}
            onInvalidateDataSource={invalidateDataSource}
            ref={spotifyPlayerRef}
            playerPaused={brainzPlayerContextRef.current.playerPaused}
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
        )}
        {userPreferences?.brainzplayer?.youtubeEnabled !== false && (
          <YoutubePlayer
            volume={brainzPlayerContextRef.current.volume}
            show={
              brainzPlayerContextRef.current.isActivated &&
              dataSourceRefs[
                brainzPlayerContextRef.current.currentDataSourceIndex
              ]?.current instanceof YoutubePlayer
            }
            onInvalidateDataSource={invalidateDataSource}
            ref={youtubePlayerRef}
            youtubeUser={youtubeAuth}
            refreshYoutubeToken={refreshYoutubeToken}
            playerPaused={brainzPlayerContextRef.current.playerPaused}
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
        )}
        {userPreferences?.brainzplayer?.soundcloudEnabled !== false && (
          <SoundcloudPlayer
            volume={brainzPlayerContextRef.current.volume}
            show={
              brainzPlayerContextRef.current.isActivated &&
              dataSourceRefs[
                brainzPlayerContextRef.current.currentDataSourceIndex
              ]?.current instanceof SoundcloudPlayer
            }
            onInvalidateDataSource={invalidateDataSource}
            ref={soundcloudPlayerRef}
            refreshSoundcloudToken={refreshSoundcloudToken}
            playerPaused={brainzPlayerContextRef.current.playerPaused}
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
        )}
        {userPreferences?.brainzplayer?.appleMusicEnabled !== false && (
          <AppleMusicPlayer
            volume={brainzPlayerContextRef.current.volume}
            show={
              brainzPlayerContextRef.current.isActivated &&
              dataSourceRefs[
                brainzPlayerContextRef.current.currentDataSourceIndex
              ]?.current instanceof AppleMusicPlayer
            }
            onInvalidateDataSource={invalidateDataSource}
            ref={appleMusicPlayerRef}
            playerPaused={brainzPlayerContextRef.current.playerPaused}
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
        )}
      </BrainzPlayerUI>
    </div>
  );
}
