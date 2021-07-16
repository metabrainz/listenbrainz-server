import * as React from "react";
import {
  isEqual as _isEqual,
  isNil as _isNil,
  isString as _isString,
  get as _get,
  has as _has,
} from "lodash";
import * as _ from "lodash";
import PlaybackControls from "./PlaybackControls";
import GlobalAppContext from "./GlobalAppContext";
import SpotifyPlayer from "./SpotifyPlayer";
import YoutubePlayer from "./YoutubePlayer";
import SoundcloudPlayer from "./SoundcloudPlayer";

export type DataSourceType = {
  playListen: (listen: Listen | JSPFTrack) => void;
  togglePlay: () => void;
  seekToPositionMs: (msTimecode: number) => void;
  isListenFromThisService: (listen: Listen | JSPFTrack) => boolean;
  canSearchAndPlayTracks: () => boolean;
};

export type DataSourceTypes = SpotifyPlayer | YoutubePlayer | SoundcloudPlayer;

export type DataSourceProps = {
  show: boolean;
  playerPaused: boolean;
  onPlayerPausedChange: (paused: boolean) => void;
  onProgressChange: (progressMs: number) => void;
  onDurationChange: (durationMs: number) => void;
  onTrackInfoChange: (title: string, artist?: string) => void;
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
      const dataSource =
        this.dataSources[currentDataSourceIndex] &&
        this.dataSources[currentDataSourceIndex].current;
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
    this.setState({ isActivated: true }, this.playNextTrack);
  };

  playListen = (
    listen: Listen | JSPFTrack,
    datasourceIndex: number = 0
  ): void => {
    this.setState({ isActivated: true });
    const { onCurrentListenChange } = this.props;
    onCurrentListenChange(listen);
    /** If available, retrieve the service the listen was listened with */
    let selectedDatasourceIndex = this.dataSources.findIndex((ds) =>
      ds.current?.isListenFromThisService(listen)
    );

    /** If no matching datasource was found, revert to the default bahaviour
     * (try playing from source 0 or try next source)
     */
    if (selectedDatasourceIndex === -1) {
      selectedDatasourceIndex = datasourceIndex;
    }

    this.stopOtherBrainzPlayers();

    this.setState({ currentDataSourceIndex: selectedDatasourceIndex }, () => {
      const { currentDataSourceIndex } = this.state;
      const dataSource =
        this.dataSources[currentDataSourceIndex] &&
        this.dataSources[currentDataSourceIndex].current;
      if (!dataSource) {
        this.invalidateDataSource();
        return;
      }

      dataSource.playListen(listen);
    });
  };

  togglePlay = async (): Promise<void> => {
    try {
      const { currentDataSourceIndex, playerPaused } = this.state;
      const dataSource =
        this.dataSources[currentDataSourceIndex] &&
        this.dataSources[currentDataSourceIndex].current;
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
    const dataSource =
      this.dataSources[currentDataSourceIndex] &&
      this.dataSources[currentDataSourceIndex].current;
    if (!dataSource) {
      this.invalidateDataSource();
      return;
    }
    dataSource.seekToPositionMs(msTimecode);
    this.progressChange(msTimecode);
  };

  toggleDirection = (): void => {
    this.setState((prevState) => {
      const direction = prevState.direction === "down" ? "up" : "down";
      return { direction };
    });
  };

  /* Listeners for datasource events */

  failedToFindTrack = (): void => {
    const { isActivated } = this.state;
    if (!isActivated) {
      // Player has not been activated by the user, do nothing.
      return;
    }

    this.playNextTrack();
  };

  playerPauseChange = (paused: boolean): void => {
    this.setState({ playerPaused: paused }, () => {
      if (paused) {
        this.stopPlayerStateTimer();
      } else {
        this.startPlayerStateTimer();
      }
    });
  };

  progressChange = (progressMs: number): void => {
    this.setState({ progressMs, updateTime: performance.now() });
  };

  durationChange = (durationMs: number): void => {
    this.setState({ durationMs }, this.startPlayerStateTimer);
  };

  trackInfoChange = (title: string, artist?: string): void => {
    this.setState({ currentTrackName: title, currentTrackArtist: artist });
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
            onTrackInfoChange={this.trackInfoChange}
            onTrackEnd={this.playNextTrack}
            onTrackNotFound={this.failedToFindTrack}
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
            onTrackInfoChange={this.trackInfoChange}
            onTrackEnd={this.playNextTrack}
            onTrackNotFound={this.failedToFindTrack}
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
            onTrackInfoChange={this.trackInfoChange}
            onTrackEnd={this.playNextTrack}
            onTrackNotFound={this.failedToFindTrack}
            handleError={this.handleError}
            handleWarning={this.handleWarning}
            handleSuccess={this.handleSuccess}
          />
        </PlaybackControls>
      </div>
    );
  }
}
