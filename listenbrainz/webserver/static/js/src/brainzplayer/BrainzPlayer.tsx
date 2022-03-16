import * as React from "react";
import {
  isEqual as _isEqual,
  isNil as _isNil,
  isString as _isString,
  get as _get,
  has as _has,
  throttle as _throttle,
  assign,
  debounce,
  cloneDeep,
  omit,
  get,
} from "lodash";
import { faPlayCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import BrainzPlayerUI from "./BrainzPlayerUI";
import GlobalAppContext from "../utils/GlobalAppContext";
import SpotifyPlayer from "./SpotifyPlayer";
import YoutubePlayer from "./YoutubePlayer";
import SoundcloudPlayer from "./SoundcloudPlayer";
import {
  hasNotificationPermission,
  createNotification,
  hasMediaSessionSupport,
  overwriteMediaSession,
  updateMediaSession,
  updateWindowTitle,
} from "../notifications/Notifications";

export type DataSourceType = {
  name: string;
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
  handleError: (error: BrainzPlayerError, title?: string) => void;
  handleWarning: (message: string | JSX.Element, title?: string) => void;
  handleSuccess: (message: string | JSX.Element, title?: string) => void;
  onInvalidateDataSource: (
    dataSource?: DataSourceTypes,
    message?: string | JSX.Element
  ) => void;
};

type BrainzPlayerProps = {
  listens: Array<Listen | JSPFTrack>;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
  refreshSpotifyToken: () => Promise<string>;
  refreshYoutubeToken: () => Promise<string>;
  listenBrainzAPIBaseURI: string;
};

type BrainzPlayerState = {
  currentListen?: Listen | JSPFTrack;
  currentDataSourceIndex: number;
  currentTrackName: string;
  currentTrackArtist?: string;
  currentTrackAlbum?: string;
  currentTrackURL?: string;
  playerPaused: boolean;
  isActivated: boolean;
  durationMs: number;
  progressMs: number;
  updateTime: number;
  listenSubmitted: boolean;
  continuousPlaybackTime: number;
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

export default class BrainzPlayer extends React.Component<
  BrainzPlayerProps,
  BrainzPlayerState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  spotifyPlayer?: React.RefObject<SpotifyPlayer>;
  youtubePlayer?: React.RefObject<YoutubePlayer>;
  soundcloudPlayer?: React.RefObject<SoundcloudPlayer>;
  dataSources: Array<React.RefObject<DataSourceTypes>> = [];

  playerStateTimerID?: NodeJS.Timeout;

  private readonly initialWindowTitle: string = window.document.title;
  private readonly mediaSessionHandlers: Array<{
    action: string;
    handler: () => void;
  }>;

  // By how much should we seek in the track?
  private SEEK_TIME_MILLISECONDS = 5000;
  // Wait X milliseconds between start of song and sending a full listen
  private SUBMIT_LISTEN_AFTER_MS = 30000;
  // Check if it's time to submit the listen every X milliseconds
  private SUBMIT_LISTEN_UPDATE_INTERVAL = 5000;

  constructor(props: BrainzPlayerProps) {
    super(props);

    this.spotifyPlayer = React.createRef<SpotifyPlayer>();
    this.dataSources.push(this.spotifyPlayer);

    this.youtubePlayer = React.createRef<YoutubePlayer>();
    this.dataSources.push(this.youtubePlayer);

    this.soundcloudPlayer = React.createRef<SoundcloudPlayer>();
    this.dataSources.push(this.soundcloudPlayer);

    this.state = {
      currentDataSourceIndex: 0,
      currentTrackName: "",
      currentTrackArtist: "",
      playerPaused: true,
      progressMs: 0,
      durationMs: 0,
      updateTime: performance.now(),
      continuousPlaybackTime: 0,
      isActivated: false,
      listenSubmitted: false,
    };

    this.mediaSessionHandlers = [
      { action: "previoustrack", handler: this.playPreviousTrack },
      { action: "nexttrack", handler: this.playNextTrack },
      { action: "seekbackward", handler: this.seekBackward },
      { action: "seekforward", handler: this.seekForward },
    ];
  }

  componentDidMount = () => {
    window.addEventListener("storage", this.onLocalStorageEvent);
    window.addEventListener("message", this.receiveBrainzPlayerMessage);
    window.addEventListener("beforeunload", this.alertBeforeClosingPage);
    // Remove SpotifyPlayer if the user doesn't have the relevant permissions to use it
    const { spotifyAuth } = this.context;
    if (
      !SpotifyPlayer.hasPermissions(spotifyAuth) &&
      this.spotifyPlayer?.current
    ) {
      this.invalidateDataSource(this.spotifyPlayer.current);
    }
  };

  componentWillUnMount = () => {
    window.removeEventListener("storage", this.onLocalStorageEvent);
    window.removeEventListener("message", this.receiveBrainzPlayerMessage);
    window.removeEventListener("beforeunload", this.alertBeforeClosingPage);
    this.stopPlayerStateTimer();
  };

  alertBeforeClosingPage = (event: BeforeUnloadEvent) => {
    const { playerPaused } = this.state;
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

  receiveBrainzPlayerMessage = (event: MessageEvent) => {
    if (event.origin !== window.location.origin) {
      // Received postMessage from different origin, ignoring it
      return;
    }
    const { brainzplayer_event, payload } = event.data;
    switch (brainzplayer_event) {
      case "play-listen":
        this.playListen(payload);
        break;
      default:
      // do nothing
    }
  };

  /** We use LocalStorage events as a form of communication between BrainzPlayers
   * that works across browser windows/tabs, to ensure only one BP is playing at a given time.
   * The event is not fired in the tab/window where the localStorage.setItem call initiated.
   */
  onLocalStorageEvent = async (event: StorageEvent) => {
    const { currentDataSourceIndex, playerPaused } = this.state;
    if (event.storageArea !== localStorage) return;
    if (event.key === "BrainzPlayer_stop") {
      const dataSource = this.dataSources[currentDataSourceIndex]?.current;
      if (dataSource && !playerPaused) {
        await dataSource.togglePlay();
      }
    }
  };

  updateWindowTitle = () => {
    const { currentTrackName } = this.state;
    updateWindowTitle(currentTrackName, "🎵", ` — ${this.initialWindowTitle}`);
  };

  reinitializeWindowTitle = () => {
    updateWindowTitle(this.initialWindowTitle);
  };

  stopOtherBrainzPlayers = (): void => {
    // Tell all other BrainzPlayer instances to please STFU
    // Using timestamp to ensure a new value each time
    window.localStorage.setItem("BrainzPlayer_stop", Date.now().toString());
  };

  isCurrentlyPlaying = (element: Listen | JSPFTrack): boolean => {
    const { currentListen } = this.state;
    if (_isNil(currentListen)) {
      return false;
    }
    if (_has(element, "identifier")) {
      // JSPF Track format
      return (element as JSPFTrack).id === (currentListen as JSPFTrack).id;
    }
    return _isEqual(element, currentListen);
  };

  playPreviousTrack = (): void => {
    this.playNextTrack(true);
  };

  playNextTrack = (invert: boolean = false): void => {
    const { listens } = this.props;
    const { isActivated } = this.state;

    if (!isActivated) {
      // Player has not been activated by the user, do nothing.
      return;
    }
    this.debouncedCheckProgressAndSubmitListen.flush();

    if (listens.length === 0) {
      this.handleWarning(
        "You can try loading listens or refreshing the page",
        "No listens to play"
      );
      return;
    }

    const currentListenIndex = listens.findIndex(this.isCurrentlyPlaying);

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

    const nextListen = listens[nextListenIndex];
    if (!nextListen) {
      this.handleWarning(
        "You can try loading more listens or refreshing the page",
        "No more listens to play"
      );
      this.reinitializeWindowTitle();
      return;
    }
    this.playListen(nextListen);
  };

  handleError = (error: BrainzPlayerError, title?: string): void => {
    const { newAlert } = this.props;
    if (!error) {
      return;
    }
    newAlert(
      "danger",
      title || "Playback error",
      _isString(error)
        ? error
        : `${!_isNil(error.status) ? `Error ${error.status}:` : ""} ${
            error.message || error.statusText
          }`
    );
  };

  handleWarning = (message: string | JSX.Element, title?: string): void => {
    const { newAlert } = this.props;
    newAlert("warning", title || "Playback error", message);
  };

  handleSuccess = (message: string | JSX.Element, title?: string): void => {
    const { newAlert } = this.props;
    newAlert("success", title || "Success", message);
  };

  handleInfoMessage = (message: string | JSX.Element, title?: string): void => {
    const { newAlert } = this.props;
    newAlert("info", title || "", message);
  };

  invalidateDataSource = (
    dataSource?: DataSourceTypes,
    message?: string | JSX.Element
  ): void => {
    let { currentDataSourceIndex: dataSourceIndex } = this.state;
    if (dataSource) {
      dataSourceIndex = this.dataSources.findIndex(
        (source) => source.current === dataSource
      );
    }
    if (dataSourceIndex >= 0) {
      if (message) {
        this.handleWarning(message, "Cannot play from this source");
      }
      this.dataSources.splice(dataSourceIndex, 1);
    }
  };

  activatePlayerAndPlay = (): void => {
    overwriteMediaSession(this.mediaSessionHandlers);
    this.setState({ isActivated: true }, this.playNextTrack);
  };

  playListen = (
    listen: Listen | JSPFTrack,
    datasourceIndex: number = 0
  ): void => {
    this.setState({
      isActivated: true,
      currentListen: listen,
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
      const listenedFromIndex = this.dataSources.findIndex((datasourceRef) => {
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

    const datasource = this.dataSources[selectedDatasourceIndex]?.current;
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
      this.playListen(listen, datasourceIndex + 1);
      return;
    }
    this.stopOtherBrainzPlayers();
    this.setState({ currentDataSourceIndex: selectedDatasourceIndex }, () => {
      datasource.playListen(listen);
    });
  };

  togglePlay = async (): Promise<void> => {
    try {
      const { currentDataSourceIndex, playerPaused } = this.state;
      const dataSource = this.dataSources[currentDataSourceIndex]?.current;
      if (!dataSource) {
        this.invalidateDataSource();
        return;
      }
      if (playerPaused) {
        this.stopOtherBrainzPlayers();
      }
      await dataSource.togglePlay();
    } catch (error) {
      this.handleError(error);
    }
  };

  getCurrentTrackName = (): string => {
    const { currentListen } = this.state;
    return _get(currentListen, "track_metadata.track_name", "");
  };

  getCurrentTrackArtists = (): string | undefined => {
    const { currentListen } = this.state;
    return _get(currentListen, "track_metadata.artist_name", "");
  };

  seekToPositionMs = (msTimecode: number): void => {
    const { currentDataSourceIndex, isActivated } = this.state;
    if (!isActivated) {
      // Player has not been activated by the user, do nothing.
      return;
    }
    const dataSource = this.dataSources[currentDataSourceIndex]?.current;
    if (!dataSource) {
      this.invalidateDataSource();
      return;
    }
    dataSource.seekToPositionMs(msTimecode);
    this.progressChange(msTimecode);
  };

  seekForward = (): void => {
    const { progressMs } = this.state;
    this.seekToPositionMs(progressMs + this.SEEK_TIME_MILLISECONDS);
  };

  seekBackward = (): void => {
    const { progressMs } = this.state;
    this.seekToPositionMs(progressMs - this.SEEK_TIME_MILLISECONDS);
  };

  /* Listeners for datasource events */

  failedToPlayTrack = (): void => {
    const { currentDataSourceIndex, isActivated } = this.state;
    if (!isActivated) {
      // Player has not been activated by the user, do nothing.
      return;
    }
    const { currentListen } = this.state;

    if (currentListen && currentDataSourceIndex < this.dataSources.length - 1) {
      // Try playing the listen with the next dataSource
      this.playListen(currentListen, currentDataSourceIndex + 1);
    } else {
      this.stopPlayerStateTimer();
      this.playNextTrack();
    }
  };

  playerPauseChange = (paused: boolean): void => {
    this.setState({ playerPaused: paused }, () => {
      if (paused) {
        this.stopPlayerStateTimer();
        this.reinitializeWindowTitle();
      } else {
        this.startPlayerStateTimer();
        this.updateWindowTitle();
      }
    });
    if (hasMediaSessionSupport()) {
      window.navigator.mediaSession.playbackState = paused
        ? "paused"
        : "playing";
    }
  };

  checkProgressAndSubmitListen = async () => {
    const { durationMs, listenSubmitted, continuousPlaybackTime } = this.state;
    const { currentUser } = this.context;
    if (!currentUser?.auth_token || listenSubmitted) {
      return;
    }
    let playbackTimeRequired = this.SUBMIT_LISTEN_AFTER_MS;
    if (durationMs > 0) {
      playbackTimeRequired = Math.min(
        this.SUBMIT_LISTEN_AFTER_MS,
        durationMs - this.SUBMIT_LISTEN_UPDATE_INTERVAL
      );
    }
    if (continuousPlaybackTime >= playbackTimeRequired) {
      const listen = this.getListenMetadataToSubmit();
      this.setState({ listenSubmitted: true });
      await this.submitListenToListenBrainz("single", listen);
    }
  };

  // eslint-disable-next-line react/sort-comp
  debouncedCheckProgressAndSubmitListen = debounce(
    this.checkProgressAndSubmitListen,
    this.SUBMIT_LISTEN_UPDATE_INTERVAL,
    {
      leading: false,
      trailing: true,
      maxWait: this.SUBMIT_LISTEN_UPDATE_INTERVAL,
    }
  );

  progressChange = (progressMs: number): void => {
    this.setState({ progressMs, updateTime: performance.now() });
  };

  durationChange = (durationMs: number): void => {
    this.setState({ durationMs }, this.startPlayerStateTimer);
  };

  trackInfoChange = (
    title: string,
    trackURL: string,
    artist?: string,
    album?: string,
    artwork?: Array<MediaImage>
  ): void => {
    this.setState(
      {
        currentTrackName: title,
        currentTrackArtist: artist,
        currentTrackURL: trackURL,
        currentTrackAlbum: album,
      },
      this.updateWindowTitle
    );
    const { playerPaused } = this.state;
    if (playerPaused) {
      // Don't send notifications or any of that if the player is not playing
      // (Avoids getting notifications upon pausing a track)
      return;
    }

    if (hasMediaSessionSupport()) {
      overwriteMediaSession(this.mediaSessionHandlers);
      updateMediaSession(title, artist, album, artwork);
    }
    // Send a notification. If user allowed browser/OS notifications use that,
    // otherwise show a toast notification on the page
    hasNotificationPermission().then((permissionGranted) => {
      if (permissionGranted) {
        createNotification(title, artist, album, artwork?.[0]?.src);
      } else {
        const message = (
          <>
            {artwork?.length ? (
              <img
                className="alert-thumbnail"
                src={artwork[0].src}
                alt={album || title}
              />
            ) : (
              <FontAwesomeIcon icon={faPlayCircle as IconProp} />
            )}
            &emsp;{title}
            {artist && ` — ${artist}`}
            {album && ` — ${album}`}
          </>
        );
        this.handleInfoMessage(message);
      }
    });

    this.submitNowPlayingToListenBrainz();
  };

  // eslint-disable-next-line react/sort-comp
  throttledTrackInfoChange = _throttle(this.trackInfoChange, 2000, {
    leading: false,
    trailing: true,
  });

  getListenMetadataToSubmit = (): BaseListenFormat => {
    const {
      currentListen,
      currentDataSourceIndex,
      currentTrackName,
      currentTrackArtist,
      currentTrackAlbum,
      currentTrackURL,
    } = this.state;
    const dataSource = this.dataSources[currentDataSourceIndex];

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

  submitNowPlayingToListenBrainz = async (): Promise<void> => {
    const newListen = this.getListenMetadataToSubmit();
    return this.submitListenToListenBrainz("playing_now", newListen);
  };

  submitListenToListenBrainz = async (
    listenType: ListenType,
    listen: BaseListenFormat,
    retries: number = 3
  ): Promise<void> => {
    const { currentUser } = this.context;
    const { currentDataSourceIndex } = this.state;
    const { listenBrainzAPIBaseURI } = this.props;
    const dataSource = this.dataSources[currentDataSourceIndex];
    if (!currentUser || !currentUser.auth_token) {
      return;
    }
    if (dataSource?.current && !dataSource.current.datasourceRecordsListens()) {
      try {
        const { auth_token } = currentUser;
        let processedPayload = listen;
        // When submitting playing_now listens, listened_at must NOT be present
        if (listenType === "playing_now") {
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
          await this.submitListenToListenBrainz(
            listenType,
            listen,
            retries - 1
          );
        } else {
          this.handleWarning(error, "Could not save this listen");
        }
      }
    }
  };

  /* Updating the progress bar without calling any API to check current player state */

  startPlayerStateTimer = (): void => {
    this.stopPlayerStateTimer();
    this.playerStateTimerID = setInterval(() => {
      this.getStatePosition();
      this.debouncedCheckProgressAndSubmitListen();
    }, 400);
  };

  getStatePosition = (): void => {
    let newProgressMs: number;
    let elapsedTimeSinceLastUpdate: number;
    const {
      playerPaused,
      durationMs,
      progressMs,
      updateTime,
      continuousPlaybackTime,
    } = this.state;
    if (playerPaused) {
      newProgressMs = progressMs || 0;
      elapsedTimeSinceLastUpdate = 0;
    } else {
      elapsedTimeSinceLastUpdate = performance.now() - updateTime;
      const position = progressMs + elapsedTimeSinceLastUpdate;
      newProgressMs = position > durationMs ? durationMs : position;
    }
    this.setState({
      progressMs: newProgressMs,
      updateTime: performance.now(),
      continuousPlaybackTime:
        continuousPlaybackTime + elapsedTimeSinceLastUpdate,
    });
  };

  stopPlayerStateTimer = (): void => {
    this.debouncedCheckProgressAndSubmitListen.flush();
    if (this.playerStateTimerID) {
      clearInterval(this.playerStateTimerID);
    }
    this.playerStateTimerID = undefined;
  };

  render() {
    const {
      currentDataSourceIndex,
      currentTrackName,
      currentTrackArtist,
      playerPaused,
      progressMs,
      durationMs,
      isActivated,
      currentListen,
    } = this.state;
    const {
      refreshSpotifyToken,
      refreshYoutubeToken,
      listenBrainzAPIBaseURI,
      newAlert,
    } = this.props;
    const { youtubeAuth, spotifyAuth } = this.context;

    return (
      <div>
        <BrainzPlayerUI
          playPreviousTrack={this.playPreviousTrack}
          playNextTrack={this.playNextTrack}
          togglePlay={
            isActivated ? this.togglePlay : this.activatePlayerAndPlay
          }
          playerPaused={playerPaused}
          trackName={currentTrackName}
          artistName={currentTrackArtist}
          progressMs={progressMs}
          durationMs={durationMs}
          seekToPositionMs={this.seekToPositionMs}
          listenBrainzAPIBaseURI={listenBrainzAPIBaseURI}
          currentListen={currentListen}
          newAlert={newAlert}
        >
          <SpotifyPlayer
            show={
              isActivated &&
              this.dataSources[currentDataSourceIndex]?.current instanceof
                SpotifyPlayer
            }
            refreshSpotifyToken={refreshSpotifyToken}
            onInvalidateDataSource={this.invalidateDataSource}
            ref={this.spotifyPlayer}
            spotifyUser={spotifyAuth}
            playerPaused={playerPaused}
            onPlayerPausedChange={this.playerPauseChange}
            onProgressChange={this.progressChange}
            onDurationChange={this.durationChange}
            onTrackInfoChange={this.throttledTrackInfoChange}
            onTrackEnd={this.playNextTrack}
            onTrackNotFound={this.failedToPlayTrack}
            handleError={this.handleError}
            handleWarning={this.handleWarning}
            handleSuccess={this.handleSuccess}
          />
          <YoutubePlayer
            show={
              isActivated &&
              this.dataSources[currentDataSourceIndex]?.current instanceof
                YoutubePlayer
            }
            onInvalidateDataSource={this.invalidateDataSource}
            ref={this.youtubePlayer}
            youtubeUser={youtubeAuth}
            refreshYoutubeToken={refreshYoutubeToken}
            playerPaused={playerPaused}
            onPlayerPausedChange={this.playerPauseChange}
            onProgressChange={this.progressChange}
            onDurationChange={this.durationChange}
            onTrackInfoChange={this.throttledTrackInfoChange}
            onTrackEnd={this.playNextTrack}
            onTrackNotFound={this.failedToPlayTrack}
            handleError={this.handleError}
            handleWarning={this.handleWarning}
            handleSuccess={this.handleSuccess}
          />
          <SoundcloudPlayer
            show={
              isActivated &&
              this.dataSources[currentDataSourceIndex]?.current instanceof
                SoundcloudPlayer
            }
            onInvalidateDataSource={this.invalidateDataSource}
            ref={this.soundcloudPlayer}
            playerPaused={playerPaused}
            onPlayerPausedChange={this.playerPauseChange}
            onProgressChange={this.progressChange}
            onDurationChange={this.durationChange}
            onTrackInfoChange={this.throttledTrackInfoChange}
            onTrackEnd={this.playNextTrack}
            onTrackNotFound={this.failedToPlayTrack}
            handleError={this.handleError}
            handleWarning={this.handleWarning}
            handleSuccess={this.handleSuccess}
          />
        </BrainzPlayerUI>
      </div>
    );
  }
}
