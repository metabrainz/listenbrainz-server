import * as React from "react";
import {
  isEqual as _isEqual,
  isNil as _isNil,
  isString as _isString,
  get as _get,
  has as _has,
  throttle as _throttle,
  assign,
} from "lodash";
import * as _ from "lodash";
import { faPlayCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import PlaybackControls from "./PlaybackControls";
import GlobalAppContext from "./GlobalAppContext";
import SpotifyPlayer from "./SpotifyPlayer";
import YoutubePlayer from "./YoutubePlayer";
import SoundcloudPlayer from "./SoundcloudPlayer";
import {
  hasNotificationPermission,
  createNotification,
  hasMediaSessionSupport,
  overwriteMediaSession,
  updateMediaSession,
} from "./Notifications";

export type DataSourceType = {
  name: string;
  playListen: (listen: Listen | JSPFTrack) => void;
  togglePlay: () => void;
  seekToPositionMs: (msTimecode: number) => void;
  isListenFromThisService: (listen: Listen | JSPFTrack) => boolean;
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
  direction: BrainzPlayDirection;
  onCurrentListenChange: (listen: Listen | JSPFTrack) => void;
  currentListen?: Listen | JSPFTrack;
  listens: Array<Listen | JSPFTrack>;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

type BrainzPlayerState = {
  currentDataSourceIndex: number;
  currentTrackName: string;
  currentTrackArtist?: string;
  direction: BrainzPlayDirection;
  playerPaused: boolean;
  isActivated: boolean;
  durationMs: number;
  progressMs: number;
  updateTime: number;
};

// By how much should we seek in the track?
const SEEK_TIME_MILLISECONDS = 5000;

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

  private readonly mediaSessionHandlers: Array<{
    action: string;
    handler: () => void;
  }>;

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
      currentTrackName: this.getCurrentTrackName(),
      currentTrackArtist: this.getCurrentTrackArtists(),
      direction: props.direction || "down",
      playerPaused: true,
      progressMs: 0,
      durationMs: 0,
      updateTime: performance.now(),
      isActivated: false,
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
    this.stopPlayerStateTimer();
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

  stopOtherBrainzPlayers = (): void => {
    // Tell all other BrainzPlayer instances to please STFU
    // Using timestamp to ensure a new value each time
    window.localStorage.setItem("BrainzPlayer_stop", Date.now().toString());
  };

  isCurrentListen = (element: Listen | JSPFTrack): boolean => {
    const { currentListen } = this.props;
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
    const { direction, isActivated } = this.state;
    if (!isActivated) {
      // Player has not been activated by the user, do nothing.
      return;
    }

    if (listens.length === 0) {
      this.handleWarning(
        "You can try loading listens or refreshing the page",
        "No listens to play"
      );
      return;
    }

    const currentListenIndex = listens.findIndex(this.isCurrentListen);

    let nextListenIndex;
    if (currentListenIndex === -1) {
      nextListenIndex = direction === "up" ? listens.length - 1 : 0;
    } else if (direction === "up") {
      nextListenIndex =
        invert === true ? currentListenIndex + 1 : currentListenIndex - 1 || 0;
    } else if (direction === "down") {
      nextListenIndex =
        invert === true ? currentListenIndex - 1 || 0 : currentListenIndex + 1;
    } else {
      this.handleWarning("Please select a song to play", "Unrecognised state");
      return;
    }

    const nextListen = listens[nextListenIndex];
    if (!nextListen) {
      this.handleWarning(
        "You can try loading more listens or refreshing the page",
        "No more listens to play"
      );
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
    this.setState({ isActivated: true });
    const { onCurrentListenChange } = this.props;
    onCurrentListenChange(listen);
    let selectedDatasourceIndex: number;
    if (datasourceIndex === 0) {
      /** If available, retrieve the service the listen was listened with */
      const listenedFromIndex = this.dataSources.findIndex((ds) =>
        ds.current?.isListenFromThisService(listen)
      );
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
      !datasource.isListenFromThisService(listen) &&
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
    const { currentListen } = this.props;
    return _get(currentListen, "track_metadata.track_name", "");
  };

  getCurrentTrackArtists = (): string | undefined => {
    const { currentListen } = this.props;
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
    this.seekToPositionMs(progressMs + SEEK_TIME_MILLISECONDS);
  };

  seekBackward = (): void => {
    const { progressMs } = this.state;
    this.seekToPositionMs(progressMs - SEEK_TIME_MILLISECONDS);
  };

  toggleDirection = (): void => {
    this.setState((prevState) => {
      const direction = prevState.direction === "down" ? "up" : "down";
      return { direction };
    });
  };

  /* Listeners for datasource events */

  failedToPlayTrack = (): void => {
    const { currentDataSourceIndex, isActivated } = this.state;
    if (!isActivated) {
      // Player has not been activated by the user, do nothing.
      return;
    }
    const { currentListen } = this.props;

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
      } else {
        this.startPlayerStateTimer();
      }
    });
    if (hasMediaSessionSupport()) {
      window.navigator.mediaSession.playbackState = paused
        ? "paused"
        : "playing";
    }
  };

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
    this.setState({ currentTrackName: title, currentTrackArtist: artist });
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

    this.submitListenToListenBrainz(title, trackURL, artist, album);
  };

  // eslint-disable-next-line react/sort-comp
  throttledTrackInfoChange = _throttle(this.trackInfoChange, 2000, {
    leading: false,
    trailing: true,
  });

  submitListenToListenBrainz = async (
    title: string,
    trackURL: string,
    artist?: string,
    album?: string
  ): Promise<void> => {
    const { APIService, currentUser } = this.context;
    const { currentDataSourceIndex } = this.state;
    const dataSource = this.dataSources[currentDataSourceIndex];
    if (!currentUser || !currentUser.auth_token) {
      return;
    }
    if (
      !!dataSource?.current &&
      !dataSource.current.datasourceRecordsListens()
    ) {
      const { listens } = this.props;
      const currentListenIndex = listens.findIndex(this.isCurrentListen);
      // Metadata we get from the datasources maybe bad quality (looking at you, Youtube… ಠ_ಠ)
      // so we use the current listen itself, and keep a trace of datasource metadata in a custom field
      const brainzplayer_metadata = {
        artist_name: artist,
        release_name: album,
        track_name: title,
      };
      try {
        // Duplicate the current listen and augment it with the datasource's metadata
        const manipulatedListen: Listen = assign(
          {},
          listens[currentListenIndex]
        ) as Listen;
        // ensure the track_metadata.additional_info path exists and add brainzplayer_metadata field
        assign(manipulatedListen, {
          track_metadata: {
            additional_info: {
              brainzplayer_metadata,
              listening_from: "listenbrainz",
              // TODO:  passs the GIT_COMMIT_SHA env variable to the globalprops and add it here as listening_from_version
              // listening_from_version: "",
              origin_url: trackURL,
              source: dataSource.current.name,
            },
          },
        });
        await APIService.submitListens(currentUser.auth_token, "single", [
          manipulatedListen,
        ]);
      } catch (error) {
        this.handleWarning(error, "Could not save this listen");
      }
    }
  };

  /* Updating the progress bar without calling any API to check current player state */

  startPlayerStateTimer = (): void => {
    this.stopPlayerStateTimer();
    this.playerStateTimerID = setInterval(() => {
      this.getStatePosition();
    }, 200);
  };

  getStatePosition = (): void => {
    let newProgressMs: number;
    const { playerPaused, durationMs, progressMs, updateTime } = this.state;
    if (playerPaused) {
      newProgressMs = progressMs || 0;
    } else {
      const position = progressMs + (performance.now() - updateTime);
      newProgressMs = position > durationMs ? durationMs : position;
    }
    this.setState({ progressMs: newProgressMs, updateTime: performance.now() });
  };

  stopPlayerStateTimer = (): void => {
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
      direction,
      progressMs,
      durationMs,
      isActivated,
    } = this.state;
    const { APIService, youtubeAuth, spotifyAuth } = this.context;
    // Determine if the user is authenticated to search & play tracks with any of the datasources
    const hasDatasourceToSearch =
      this.dataSources.findIndex((ds) =>
        ds.current?.canSearchAndPlayTracks()
      ) !== -1;
    return (
      <div>
        <PlaybackControls
          playPreviousTrack={this.playPreviousTrack}
          playNextTrack={this.playNextTrack}
          togglePlay={
            isActivated ? this.togglePlay : this.activatePlayerAndPlay
          }
          playerPaused={playerPaused}
          toggleDirection={this.toggleDirection}
          direction={direction}
          trackName={currentTrackName}
          artistName={currentTrackArtist}
          progressMs={progressMs}
          durationMs={durationMs}
          seekToPositionMs={this.seekToPositionMs}
        >
          {!hasDatasourceToSearch && (
            <div className="connect-services-message">
              You need to{" "}
              <a href="/profile/music-services/details/" target="_blank">
                connect to a music service
              </a>{" "}
              and refresh this page in order to search for and play songs on
              ListenBrainz.
            </div>
          )}
          <SpotifyPlayer
            show={
              isActivated &&
              this.dataSources[currentDataSourceIndex]?.current instanceof
                SpotifyPlayer
            }
            refreshSpotifyToken={APIService.refreshSpotifyToken}
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
            refreshYoutubeToken={APIService.refreshYoutubeToken}
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
        </PlaybackControls>
      </div>
    );
  }
}
