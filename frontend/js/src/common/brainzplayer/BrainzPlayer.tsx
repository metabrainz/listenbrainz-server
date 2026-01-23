import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faPlayCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  has as _has,
  isEqual as _isEqual,
  isNil as _isNil,
  isString as _isString,
  throttle as _throttle,
  debounce,
  omit,
  union,
} from "lodash";
import * as React from "react";
import { toast } from "react-toastify";
import { Link, useLocation } from "react-router";
import { Helmet } from "react-helmet";
import { useAtom, useAtomValue, useSetAtom, useStore } from "jotai";
import { useResetAtom } from "jotai/utils";
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
import InternetArchivePlayer from "./InternetArchivePlayer";
import FunkwhalePlayer from "./FunkwhalePlayer";
import NavidromePlayer from "./NavidromePlayer";
import {
  DataSourceKey,
  defaultDataSourcesPriority,
} from "../../settings/brainzplayer/BrainzPlayerSettings";

// Atoms
import {
  QueueRepeatModes,
  playerPausedAtom,
  setPlaybackTimerAtom,
  durationMsAtom,
  volumeAtom,
  progressMsAtom,
  updateTimeAtom,
  queueRepeatModeAtom,
  listenSubmittedAtom,
  continuousPlaybackTimeAtom,
  currentTrackNameAtom,
  currentTrackArtistAtom,
  currentTrackAlbumAtom,
  currentTrackURLAtom,
  currentTrackCoverURLAtom,
  currentDataSourceIndexAtom,
  currentDataSourceNameAtom,
  currentListenAtom,
  queueAtom,
  ambientQueueAtom,
  currentListenIndexAtom,
  addListenToBottomOfQueueAtom,
  replaceQueueAndResetAtom,
  isActivatedAtom,
  clearQueuesBeforeListenAndSetQueuesAtom,
} from "./BrainzPlayerAtoms";

import useWindowTitle from "./hooks/useWindowTitle";
import useCrossTabSync from "./hooks/useCrossTabSync";
import useListenSubmission from "./hooks/useListenSubmission";

export type DataSourceType = {
  name: string;
  icon: IconProp;
  iconColor: string;
  playListen: (listen: Listen | JSPFTrack) => void;
  togglePlay: () => void;
  stop: () => void;
  seekToPositionMs: (msTimecode: number) => void;
  canSearchAndPlayTracks: () => boolean;
  datasourceRecordsListens: () => boolean;
};

export type DataSourceTypes =
  | SpotifyPlayer
  | YoutubePlayer
  | SoundcloudPlayer
  | AppleMusicPlayer
  | InternetArchivePlayer
  | FunkwhalePlayer
  | NavidromePlayer;

export type DataSourceProps = {
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
  if (datasource instanceof FunkwhalePlayer) {
    return FunkwhalePlayer.isListenFromThisService(listen);
  }
  if (datasource instanceof NavidromePlayer) {
    return NavidromePlayer.isListenFromThisService(listen);
  }
  if (datasource instanceof InternetArchivePlayer) {
    return InternetArchivePlayer.isListenFromThisService(listen);
  }
  return undefined;
}

export default function BrainzPlayer() {
  // Global App Context
  const globalAppContext = React.useContext(GlobalAppContext);
  const {
    APIService,
    currentUser,
    spotifyAuth,
    youtubeAuth,
    soundcloudAuth,
    appleAuth,
    funkwhaleAuth,
    navidromeAuth,
    userPreferences,
  } = globalAppContext;

  const {
    refreshSpotifyToken,
    refreshYoutubeToken,
    refreshSoundcloudToken,
    refreshFunkwhaleToken: apiRefreshFunkwhaleToken,
    APIBaseURI: listenBrainzAPIBaseURI,
  } = APIService;

  const store = useStore();

  // Refs for local state
  const isActivatedRef = React.useRef(useAtomValue(isActivatedAtom));
  const activatePlayer = async () => {
    if (isActivatedRef.current === true) {
      return;
    }
    isActivatedRef.current = true;
    store.set(isActivatedAtom, true);
    await new Promise((resolve) => {
      setTimeout(resolve, 1000);
    });
  };

  // Context Atoms - Values
  const volume = useAtomValue(volumeAtom);
  const queueRepeatMode = useAtomValue(queueRepeatModeAtom);

  // Context Atoms - Setters
  const setUpdateTime = useSetAtom(updateTimeAtom);
  const setProgressMs = useSetAtom(progressMsAtom);
  const resetListenSubmitted = useResetAtom(listenSubmittedAtom);
  const resetContinuousPlaybackTime = useResetAtom(continuousPlaybackTimeAtom);
  const setCurrentTrackCoverURL = useSetAtom(currentTrackCoverURLAtom);
  const setCurrentTrackName = useSetAtom(currentTrackNameAtom);
  const setCurrentTrackArtist = useSetAtom(currentTrackArtistAtom);
  const setCurrentTrackAlbum = useSetAtom(currentTrackAlbumAtom);
  const setCurrentTrackURL = useSetAtom(currentTrackURLAtom);
  const setCurrentDataSourceName = useSetAtom(currentDataSourceNameAtom);
  const setQueue = useSetAtom(queueAtom);
  const setAmbientQueue = useSetAtom(ambientQueueAtom);
  const setCurrentListenIndex = useSetAtom(currentListenIndexAtom);
  const setCurrentListen = useSetAtom(currentListenAtom);
  const setDurationMs = useSetAtom(durationMsAtom);

  const [playerPaused, setPlayerPaused] = useAtom(playerPausedAtom);
  const [currentDataSourceIndex, setCurrentDataSourceIndex] = useAtom(
    currentDataSourceIndexAtom
  );

  // Action Atoms
  const updatePlayerProgressBar = useSetAtom(setPlaybackTimerAtom);
  const addListenToBottomOfQueue = useSetAtom(addListenToBottomOfQueueAtom);
  const replaceQueueAndReset = useSetAtom(replaceQueueAndResetAtom);
  const addOrSkipToListenInQueue = useSetAtom(
    clearQueuesBeforeListenAndSetQueuesAtom
  );

  const getProgressMs = () => store.get(progressMsAtom);
  const getQueue = () => store.get(queueAtom);
  const getAmbientQueue = () => store.get(ambientQueueAtom);
  const getCurrentListenIndex = () => store.get(currentListenIndexAtom);
  const getCurrentListen = () => store.get(currentListenAtom);
  const getCurrentDataSourceIndex = () => store.get(currentDataSourceIndexAtom);
  const getPlayerPaused = () => store.get(playerPausedAtom);
  // Wrapper for funkwhale token refresh that gets the host URL from context
  const refreshFunkwhaleToken = React.useCallback(async () => {
    const hostUrl = funkwhaleAuth?.instance_url;
    if (!hostUrl) {
      throw new Error("No Funkwhale instance URL found in context");
    }
    if (!currentUser?.auth_token) {
      throw new Error("No user authentication token available");
    }

    try {
      return await apiRefreshFunkwhaleToken(currentUser.auth_token, hostUrl);
    } catch (error) {
      // Check if this is an authentication error that requires reconnection
      if (error.status === 401 || error.status === 403) {
        const errorMessage = error.message || "";
        if (
          errorMessage.includes("no longer valid") ||
          errorMessage.includes("reconnect") ||
          errorMessage.includes("revoked authorization")
        ) {
          throw new Error(
            "Funkwhale connection is no longer valid. Please reconnect to this server in your music service settings."
          );
        }
        throw new Error(
          "Funkwhale authentication failed. Please re-authenticate in your music service settings."
        );
      }
      if (error.status === 503) {
        throw new Error(
          "Funkwhale service is temporarily unavailable. Please try again later."
        );
      }
      throw new Error(`Token refresh failed: ${error.message}`);
    }
  }, [
    apiRefreshFunkwhaleToken,
    funkwhaleAuth?.instance_url,
    currentUser?.auth_token,
  ]);

  // Constants
  // By how much should we seek in the track?
  const SEEK_TIME_MILLISECONDS = 5000;
  // Wait X milliseconds between start of song and sending a full listen
  const SUBMIT_LISTEN_AFTER_MS = 30000;
  // Check if it's time to submit the listen every X milliseconds
  const SUBMIT_LISTEN_UPDATE_INTERVAL = 5000;

  const {
    spotifyEnabled = true,
    appleMusicEnabled = true,
    funkwhaleEnabled = true,
    navidromeEnabled = true,
    soundcloudEnabled = true,
    youtubeEnabled = true,
    internetArchiveEnabled = true,
    brainzplayerEnabled = true,
    dataSourcesPriority = defaultDataSourcesPriority,
  } = userPreferences?.brainzplayer ?? {};

  const brainzPlayerDisabled =
    brainzplayerEnabled === false ||
    (spotifyEnabled === false &&
      youtubeEnabled === false &&
      soundcloudEnabled === false &&
      internetArchiveEnabled === false &&
      funkwhaleEnabled === false &&
      navidromeEnabled === false &&
      appleMusicEnabled === false);

  const enabledDataSources = [
    spotifyEnabled && SpotifyPlayer.hasPermissions(spotifyAuth) && "spotify",
    appleMusicEnabled &&
      AppleMusicPlayer.hasPermissions(appleAuth) &&
      "appleMusic",
    funkwhaleEnabled &&
      FunkwhalePlayer.hasPermissions(funkwhaleAuth) &&
      "funkwhale",
    navidromeEnabled &&
      NavidromePlayer.hasPermissions(navidromeAuth) &&
      "navidrome",
    soundcloudEnabled &&
      SoundcloudPlayer.hasPermissions(soundcloudAuth) &&
      "soundcloud",
    youtubeEnabled && "youtube",
    internetArchiveEnabled && "internetArchive",
  ].filter(Boolean) as DataSourceKey[];

  // Use the enabled sources to filter the priority list
  // Combine saved priority list and default list to add any new music service at the end
  // then filter out disabled datasources (new ones will be enabled by default)
  const sortedDataSources = union(
    dataSourcesPriority,
    defaultDataSourcesPriority
  ).filter((key) => enabledDataSources.includes(key));

  // Refs
  const spotifyPlayerRef = React.useRef<SpotifyPlayer>(null);
  const youtubePlayerRef = React.useRef<YoutubePlayer>(null);
  const soundcloudPlayerRef = React.useRef<SoundcloudPlayer>(null);
  const appleMusicPlayerRef = React.useRef<AppleMusicPlayer>(null);
  const internetArchivePlayerRef = React.useRef<InternetArchivePlayer>(null);
  const funkwhalePlayerRef = React.useRef<FunkwhalePlayer>(null);
  const navidromePlayerRef = React.useRef<NavidromePlayer>(null);
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
        case "internetArchive":
          dataSources.push(internetArchivePlayerRef);
          break;
        case "funkwhale":
          dataSources.push(funkwhalePlayerRef);
          break;
        case "navidrome":
          dataSources.push(navidromePlayerRef);
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

  // Hooks
  const {
    htmlTitle,
    setHtmlTitle,
    currentHTMLTitle,
    updateWindowTitleWithTrackName,
    reinitializeWindowTitle,
  } = useWindowTitle();

  const { submitCurrentListen, submitNowPlaying } = useListenSubmission({
    currentUser,
    listenBrainzAPIBaseURI,
    dataSourceRefs,
  });

  // Create a callback function to pause playback for current source, used for cross-tab syncing
  const pauseCurrentPlayback = async (): Promise<void> => {
    try {
      const dataSource = dataSourceRefs[getCurrentDataSourceIndex()]?.current;
      dataSource?.stop();
    } catch (error) {
      handleError(error, "Could not pause playback");
    }
  };
  const { stopOtherBrainzPlayers } = useCrossTabSync(pauseCurrentPlayback);

  // eslint-disable-next-line react/sort-comp
  const debouncedCheckProgressAndSubmitListen = React.useMemo(() => {
    const checkProgressAndSubmitListen = async () => {
      const listenWasSubmitted = store.get(listenSubmittedAtom);
      if (!currentUser?.auth_token || listenWasSubmitted) {
        return;
      }
      const duration = store.get(durationMsAtom);
      const continuousPlaybackTime = store.get(continuousPlaybackTimeAtom);
      let playbackTimeRequired = SUBMIT_LISTEN_AFTER_MS;
      if (duration > 0) {
        playbackTimeRequired = Math.min(
          SUBMIT_LISTEN_AFTER_MS,
          duration - SUBMIT_LISTEN_UPDATE_INTERVAL
        );
      }

      if (continuousPlaybackTime >= playbackTimeRequired) {
        submitCurrentListen();
      }
    };
    return debounce(
      checkProgressAndSubmitListen,
      SUBMIT_LISTEN_UPDATE_INTERVAL,
      {
        leading: false,
        trailing: true,
        maxWait: SUBMIT_LISTEN_UPDATE_INTERVAL,
      }
    );
  }, [currentUser?.auth_token, store, submitCurrentListen]);

  const playListen = async (
    listen: BrainzPlayerQueueItem,
    nextListenIndex: number,
    datasourceIndex: number = 0
  ): Promise<void> => {
    setCurrentListenIndex(nextListenIndex);
    setCurrentListen(listen);
    resetContinuousPlaybackTime();
    resetListenSubmitted();

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

    const dataSource = dataSourceRefs[selectedDatasourceIndex]?.current;
    if (!dataSource) {
      await new Promise((resolve) => {
        setTimeout(resolve, 200);
      });
      playListen(listen, nextListenIndex, datasourceIndex);
      return;
    }
    // Check if we can play the listen with the selected datasource
    // otherwise skip to the next datasource without trying or setting currentDataSourceIndex
    // This prevents rendering datasource iframes when we can't use the datasource
    if (
      !isListenFromDatasource(listen, dataSource) &&
      !dataSource.canSearchAndPlayTracks()
    ) {
      playListen(listen, nextListenIndex, datasourceIndex + 1);
      return;
    }
    stopOtherBrainzPlayers();
    setCurrentDataSourceIndex(selectedDatasourceIndex);
    setCurrentDataSourceName(dataSource.name);
    // Make sure the datasource is ready to play
    try {
      await new Promise<void>((resolve, reject) => {
        // Early exit if already set
        if (store.get(currentDataSourceIndexAtom) === selectedDatasourceIndex) {
          resolve();
          return;
        }
        let iterations = 0;
        const checkDataSourceReadyInterval = setInterval(() => {
          if (
            store.get(currentDataSourceIndexAtom) === selectedDatasourceIndex
          ) {
            clearInterval(checkDataSourceReadyInterval);
            resolve();
          } else if (iterations >= 6) {
            clearInterval(checkDataSourceReadyInterval);
            reject();
          } else {
            iterations += 1;
          }
        }, 500);
      });
    } catch (e) {
      playListen(listen, nextListenIndex, datasourceIndex + 1);
      return;
    }
    dataSource.playListen(getCurrentListen() ?? listen);
  };

  const stopPlayerStateTimer = React.useCallback((): void => {
    debouncedCheckProgressAndSubmitListen.flush();
    if (playerStateTimerID.current) {
      clearInterval(playerStateTimerID.current);
    }
    playerStateTimerID.current = null;
  }, [debouncedCheckProgressAndSubmitListen]);

  const playNextTrack = (invert: boolean = false): void => {
    if (!isActivatedRef.current) {
      // Player has not been activated by the user, do nothing.
      return;
    }
    debouncedCheckProgressAndSubmitListen.flush();

    const currentQueue = getQueue();
    const currentAmbientQueue = getAmbientQueue();

    if (currentQueue.length === 0 && currentAmbientQueue.length === 0) {
      handleWarning(
        "You can try loading listens or refreshing the page",
        "No listens to play"
      );
      return;
    }

    const currentPlayingListenIndex = getCurrentListenIndex();

    let nextListenIndex: number;
    // If the queue repeat mode is one, then play the same track again
    if (queueRepeatMode === QueueRepeatModes.one) {
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
      playListen(nextListen, nextListenIndex);
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
        addListenToBottomOfQueue(ambientQueueTop);
        setAmbientQueue(currentAmbientQueue);
        // Not enough time for the queue to be updated,
        // use the listen we just added to the bottom of the queue
        playListen(ambientQueueTop, currentQueueLength);
        return;
      }
    } else if (queueRepeatMode === QueueRepeatModes.off) {
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
    playListen(nextListen, nextListenIndex);
  };

  const playPreviousTrack = (): void => {
    playNextTrack(true);
  };

  const startPlayerStateTimer = React.useCallback((): void => {
    stopPlayerStateTimer();
    playerStateTimerID.current = setInterval(() => {
      updatePlayerProgressBar();
      debouncedCheckProgressAndSubmitListen();
    }, 400);
  }, [
    debouncedCheckProgressAndSubmitListen,
    stopPlayerStateTimer,
    updatePlayerProgressBar,
  ]);

  const failedToPlayTrack = (): void => {
    if (!isActivatedRef.current) {
      // Player has not been activated by the user, do nothing.
      return;
    }
    stopPlayerStateTimer();
    const currDataSourceIndex = getCurrentDataSourceIndex();
    const currentListenFresh = getCurrentListen();
    // Stop playback on the previous datasource, if playing
    const currentDataSource = dataSourceRefs[currDataSourceIndex]?.current;
    if (currentDataSource && !getPlayerPaused()) {
      currentDataSource.stop();
    }
    if (currentListenFresh && currDataSourceIndex < dataSourceRefs.length - 1) {
      // Try playing the listen with the next dataSource
      playListen(
        currentListenFresh,
        getCurrentListenIndex(),
        currDataSourceIndex + 1
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
      playNextTrack();
    }
  };

  const invalidateDataSource = (
    dataSource?: DataSourceTypes,
    message?: string | JSX.Element
  ): void => {
    stopPlayerStateTimer();
    let dataSourceIndex = getCurrentDataSourceIndex();
    if (dataSource) {
      dataSource.stop();
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
    if (getCurrentListen()) {
      // If currently trying to play a track, declare a failure
      failedToPlayTrack();
    }
  };

  const progressChange = (newProgressMs: number): void => {
    setProgressMs(newProgressMs);
    setUpdateTime(performance.now());
  };

  const seekToPositionMs = (msTimecode: number): void => {
    if (!isActivatedRef.current) {
      // Player has not been activated by the user, do nothing.
      return;
    }
    const dataSource = dataSourceRefs[getCurrentDataSourceIndex()]?.current;
    if (!dataSource) {
      invalidateDataSource();
      return;
    }
    dataSource.seekToPositionMs(msTimecode);
    progressChange(msTimecode);
  };

  const seekForward = (): void => {
    seekToPositionMs(getProgressMs() + SEEK_TIME_MILLISECONDS);
  };

  const seekBackward = (): void => {
    seekToPositionMs(getProgressMs() - SEEK_TIME_MILLISECONDS);
  };
  const handleNumberKeySkip = React.useCallback(
    (event: KeyboardEvent) => {
      if (process.env.NODE_ENV === "test") {
        return;
      }

      const keyAsNumber = Number(event.key);
      if (
        !Number.isInteger(keyAsNumber) ||
        keyAsNumber < 0 ||
        keyAsNumber > 9
      ) {
        return;
      }

      const target = event.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      if (getPlayerPaused()) {
        return;
      }

      event.preventDefault();

      const durationMs = store.get(durationMsAtom);
      if (!durationMs) {
        return;
      }

      const seekToMs = (durationMs * keyAsNumber * 10) / 100;
      seekToPositionMs(seekToMs);
    },
    [store, getPlayerPaused, seekToPositionMs]
  );

  React.useEffect(() => {
    window.addEventListener("keydown", handleNumberKeySkip, true);
    return () => {
      window.removeEventListener("keydown", handleNumberKeySkip, true);
    };
  }, [handleNumberKeySkip]);

  const mediaSessionHandlers = [
    { action: "previoustrack", handler: playPreviousTrack },
    { action: "nexttrack", handler: playNextTrack },
    { action: "seekbackward", handler: seekBackward },
    { action: "seekforward", handler: seekForward },
  ];

  const activatePlayerAndPlay = async () => {
    await activatePlayer();
    overwriteMediaSession(mediaSessionHandlers);
    playNextTrack();
  };

  const togglePlay = () => {
    try {
      const dataSource = dataSourceRefs[getCurrentDataSourceIndex()]?.current;
      if (!dataSource) {
        invalidateDataSource();
        return;
      }
      if (playerPaused) {
        stopOtherBrainzPlayers();
      }
      dataSource.togglePlay();
    } catch (error) {
      handleError(error, "Could not play");
    }
  };

  /* Listeners for datasource events */

  const playerPauseChange = (paused: boolean): void => {
    setPlayerPaused(paused);
    if (paused) {
      stopPlayerStateTimer();
      reinitializeWindowTitle();
    } else {
      startPlayerStateTimer();
      updateWindowTitleWithTrackName();
    }
    if (hasMediaSessionSupport()) {
      window.navigator.mediaSession.playbackState = paused
        ? "paused"
        : "playing";
    }
  };

  const durationChange = (newDurationMs: number): void => {
    setDurationMs(newDurationMs);
  };

  const trackInfoChange = (
    title: string,
    trackURL: string,
    artist?: string,
    album?: string,
    artwork?: Array<MediaImage>
  ): void => {
    setCurrentTrackName(title);
    setCurrentTrackArtist(artist!);
    setCurrentTrackAlbum(album);
    setCurrentTrackURL(trackURL);
    setCurrentTrackCoverURL(artwork?.[0]?.src);

    updateWindowTitleWithTrackName();
    if (store.get(playerPausedAtom)) {
      // Don't send notifications or any of that if the player is not playing
      // (Avoids getting notifications upon pausing a track)
      return;
    }
    submitNowPlaying();

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
                // eslint-disable-next-line no-console
                onError={console.error}
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
    const currentQueue = getQueue();

    // Clear the queue by keeping only the currently playing song
    const currentPlayingListenIndex = getCurrentListenIndex();
    setQueue(
      currentQueue[currentPlayingListenIndex]
        ? [currentQueue[currentPlayingListenIndex]]
        : []
    );
    setCurrentListenIndex(0);
  };

  const playNextListenFromQueue = (): void => {
    const currentPlayingListenIndex = getCurrentListenIndex();
    const nextTrack = getQueue()[currentPlayingListenIndex + 1];
    playListen(nextTrack, currentPlayingListenIndex + 1);
  };

  const playListenEventHandler = (listen: Listen | JSPFTrack) => {
    addOrSkipToListenInQueue(listen);
    playNextListenFromQueue();
  };

  const playAmbientQueue = (tracks: (Listen | JSPFTrack)[]): void => {
    replaceQueueAndReset(tracks);
    playNextTrack();
  };

  // eslint-disable-next-line react/sort-comp
  const throttledTrackInfoChange = _throttle(trackInfoChange, 2000, {
    leading: false,
    trailing: true,
  });

  const receiveBrainzPlayerMessage = async (event: MessageEvent) => {
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
    if (
      !["play-listen", "force-play", "play-ambient-queue"].includes(
        brainzplayer_event
      )
    ) {
      // Ignore events that are not related to playing a track
      return;
    }
    await activatePlayer();
    pauseCurrentPlayback();
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
    if (
      !NavidromePlayer.hasPermissions(navidromeAuth) &&
      navidromePlayerRef?.current
    ) {
      invalidateDataSource(navidromePlayerRef.current);
    }
    if (
      !AppleMusicPlayer.hasPermissions(appleAuth) &&
      appleMusicPlayerRef?.current
    ) {
      invalidateDataSource(appleMusicPlayerRef.current);
    }
    if (
      !FunkwhalePlayer.hasPermissions(funkwhaleAuth) &&
      funkwhalePlayerRef?.current
    ) {
      invalidateDataSource(funkwhalePlayerRef.current);
    }
    return () => {
      window.removeEventListener("message", receiveBrainzPlayerMessage);
      window.removeEventListener("beforeunload", alertBeforeClosingPage);
      stopPlayerStateTimer();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spotifyAuth, soundcloudAuth, navidromeAuth, appleAuth, funkwhaleAuth]);

  const { pathname } = useLocation();

  // Hide the player if user is on homepage and the player is not activated, and there is nothing in either queues
  if (
    pathname === "/" &&
    !isActivatedRef.current &&
    getQueue().length === 0 &&
    getAmbientQueue().length === 0
  ) {
    return null;
  }
  const currentDataSource = dataSourceRefs[currentDataSourceIndex]?.current;

  return (
    <div
      data-testid="brainzplayer"
      className={!brainzplayerEnabled ? "hidden" : ""}
    >
      {!playerPaused && (
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
        togglePlay={isActivatedRef.current ? togglePlay : activatePlayerAndPlay}
        seekToPositionMs={seekToPositionMs}
        listenBrainzAPIBaseURI={listenBrainzAPIBaseURI}
        currentDataSource={currentDataSource}
        clearQueue={clearQueue}
      >
        {Boolean(isActivatedRef.current) && (
          <>
            {spotifyEnabled !== false && (
              <SpotifyPlayer
                volume={volume}
                refreshSpotifyToken={refreshSpotifyToken}
                onInvalidateDataSource={invalidateDataSource}
                ref={spotifyPlayerRef}
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
            )}
            {youtubeEnabled !== false && (
              <YoutubePlayer
                volume={volume}
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
            )}
            {soundcloudEnabled !== false && (
              <SoundcloudPlayer
                volume={volume}
                onInvalidateDataSource={invalidateDataSource}
                ref={soundcloudPlayerRef}
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
            )}
            {funkwhaleEnabled !== false && (
              <FunkwhalePlayer
                volume={volume}
                onInvalidateDataSource={invalidateDataSource}
                ref={funkwhalePlayerRef}
                refreshFunkwhaleToken={refreshFunkwhaleToken}
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
            )}
            {appleMusicEnabled !== false && (
              <AppleMusicPlayer
                volume={volume}
                onInvalidateDataSource={invalidateDataSource}
                ref={appleMusicPlayerRef}
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
            )}
            {navidromeEnabled !== false && (
              <NavidromePlayer
                volume={volume}
                onInvalidateDataSource={invalidateDataSource}
                ref={navidromePlayerRef}
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
            )}
            {internetArchiveEnabled !== false && (
              <InternetArchivePlayer
                volume={volume}
                ref={internetArchivePlayerRef}
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
                onInvalidateDataSource={invalidateDataSource}
              />
            )}
          </>
        )}
      </BrainzPlayerUI>
    </div>
  );
}
