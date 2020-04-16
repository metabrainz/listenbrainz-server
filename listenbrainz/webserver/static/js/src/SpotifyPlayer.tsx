import * as React from "react";
import { isEqual as _isEqual } from "lodash";
import * as _ from "lodash";
import PlaybackControls from "./PlaybackControls";
import { searchForSpotifyTrack } from "./utils";
import APIService from "./APIService";

const getSpotifyUriFromListen = (listen: Listen): string => {
  if (
    !listen ||
    !listen.track_metadata ||
    !listen.track_metadata.additional_info ||
    typeof listen.track_metadata.additional_info.spotify_id !== "string"
  ) {
    return "";
  }
  const spotifyId = listen.track_metadata.additional_info.spotify_id;
  const spotifyTrack = spotifyId.split("https://open.spotify.com/")[1];
  if (typeof spotifyTrack !== "string") {
    return "";
  }
  return `spotify:${spotifyTrack.replace("/", ":")}`;
};

// Fix for LB-447 (Player does not play any sound)
// https://github.com/spotify/web-playback-sdk/issues/75#issuecomment-487325589
const fixSpotifyPlayerStyleIssue = () => {
  const iframe = document.querySelector(
    'iframe[src="https://sdk.scdn.co/embedded/index.html"]'
  ) as any; // TODO: this is hacky, but this whole function seems hacky tbh
  if (iframe) {
    iframe.style.display = "block";
    iframe.style.position = "absolute";
    iframe.style.top = "-1000px";
    iframe.style.left = "-1000px";
  }
};

type SpotifyPlayerProps = {
  spotifyUser: SpotifyUser;
  direction: SpotifyPlayDirection;
  onPermissionError?: (message: string) => void;
  onCurrentListenChange: (listen: Listen) => void;
  currentListen?: Listen;
  listens: Array<Listen>;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
  apiService: APIService;
  onAccountError: (message: string | JSX.Element) => void;
};

type SpotifyPlayerState = {
  accessToken: string;
  permission: SpotifyPermission;
  currentSpotifyTrack: SpotifyTrack;
  playerPaused: boolean;
  progressMs: number;
  durationMs: number;
  direction: SpotifyPlayDirection;
  paused?: boolean;
  position?: number;
  duration?: number;
  trackWindow?: SpotifyPlayerTrackWindow;
};

export default class SpotifyPlayer extends React.Component<
  SpotifyPlayerProps,
  SpotifyPlayerState
> {
  spotifyPlayer?: SpotifyPlayerType;

  firstRun: boolean = true;

  playerStateTimerID?: number | null;
  debouncedPlayNextTrack: () => void;

  constructor(props: SpotifyPlayerProps) {
    super(props);
    this.state = {
      accessToken: props.spotifyUser.access_token,
      permission: props.spotifyUser.permission,
      currentSpotifyTrack: {} as SpotifyTrack,
      playerPaused: true,
      progressMs: 0,
      durationMs: 0,
      direction: props.direction || "down",
    };

    this.debouncedPlayNextTrack = _.debounce(this.playNextTrack, 500, {
      leading: true,
      trailing: false,
    });

    const { accessToken, permission } = this.state;

    // Do an initial check of the spotify token permissions (scopes) before loading the SDK library
    this.checkSpotifyToken(accessToken, permission).then((success) => {
      if (success) {
        window.onSpotifyWebPlaybackSDKReady = this.connectSpotifyPlayer;
        const spotifyPlayerSDKLib = require("../lib/spotify-player-sdk-1.6.0"); // eslint-disable-line global-require
      }
    });
  }

  componentWillUnmount(): void {
    this.disconnectSpotifyPlayer();
  }

  searchAndPlayTrack = (listen: Listen): void => {
    const trackName = _.get(listen, "track_metadata.track_name");
    const artistName = _.get(listen, "track_metadata.artist_name");
    const releaseName = _.get(listen, "track_metadata.release_name");
    if (!trackName) {
      this.handleWarning("Not enough info to search on Spotify");
    }
    const { accessToken } = this.state;

    searchForSpotifyTrack(accessToken, trackName, artistName, releaseName)
      .then((track) => {
        // Track should be a Spotify track object:
        // https://developer.spotify.com/documentation/web-api/reference/object-model/#track-object-full
        if (_.has(track, "name") && _.has(track, "id") && _.has(track, "uri")) {
          this.handleSuccess(
            <span>
              We found a matching track on Spotify:
              <br />
              {track.name} —{" "}
              <small>
                {track.artists
                  .map((artist: SpotifyArtist) => artist.name)
                  .join(", ")}
              </small>
            </span>,
            "Found a match"
          );
          this.playSpotifyURI(track.uri);
          return;
        }
        this.handleWarning("Could not find track on Spotify");
        this.playNextTrack();
      })
      .catch((errorObject) => {
        if (errorObject.status === 401) {
          // Handle token error and try again if fixed
          this.handleTokenError(
            errorObject.message,
            this.searchAndPlayTrack.bind(this, listen)
          );
          return;
        }
        if (errorObject.status === 403) {
          this.handleAccountError();
          return;
        }
        this.handleError(errorObject.message);
      });
  };

  playSpotifyURI = (spotifyURI: string): void => {
    const { accessToken } = this.state;
    if (!this.spotifyPlayer) {
      this.connectSpotifyPlayer(this.playSpotifyURI.bind(this, spotifyURI));
    }
    fetch(
      `https://api.spotify.com/v1/me/player/play?device_id=${this.spotifyPlayer._options.id}`, // eslint-disable-line no-underscore-dangle
      {
        method: "PUT",
        body: JSON.stringify({ uris: [spotifyURI] }),
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
      }
    )
      .then((response) => {
        if (response.status === 401) {
          // Handle token error and try again if fixed
          this.handleTokenError(
            response.statusText,
            this.playSpotifyURI.bind(this, spotifyURI)
          );
          return;
        }
        if (response.status === 403) {
          this.handleAccountError();
          return;
        }
        if (response.status === 404) {
          // Device not found
          // Reconnect and try again
          this.connectSpotifyPlayer(this.playSpotifyURI.bind(this, spotifyURI));
          return;
        }
        if (!response.ok) {
          this.handleError(response.statusText);
        }
      })
      .catch((error) => {
        this.handleError(error.message);
      });
  };

  checkSpotifyToken = async (
    accessToken?: string,
    permission?: string
  ): Promise<boolean> => {
    const { onPermissionError } = this.props;
    if (!accessToken || !permission) {
      this.handleAccountError();
      return false;
    }
    try {
      const scopes = permission.split(" ");
      const requiredScopes = [
        "streaming",
        "user-read-email",
        "user-read-private",
      ];
      for (let i = 0; i < requiredScopes.length; i += 1) {
        if (!scopes.includes(requiredScopes[i])) {
          if (onPermissionError) {
            onPermissionError("Permission to play songs not granted");
          }
          return false;
        }
      }
      return true;
    } catch (error) {
      this.handleError(error);
      return false;
    }
  };

  playListen = (listen: Listen): void => {
    const { onCurrentListenChange } = this.props;
    onCurrentListenChange(listen);
    if (_.get(listen, "track_metadata.additional_info.spotify_id")) {
      this.playSpotifyURI(getSpotifyUriFromListen(listen));
    } else {
      this.searchAndPlayTrack(listen);
    }
  };

  isCurrentListen = (element: Listen): boolean => {
    const { currentListen } = this.props;
    return (currentListen && _isEqual(element, currentListen)) as boolean;
  };

  playPreviousTrack = (): void => {
    this.playNextTrack(true);
  };

  playNextTrack = (invert: boolean = false): void => {
    const { listens } = this.props;
    const { direction } = this.state;

    if (listens.length === 0) {
      this.handleWarning(
        "You can try loading listens or refreshing the page",
        "No Spotify listens to play"
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
        "No more Spotify listens to play"
      );
      return;
    }

    this.playListen(nextListen);
  };

  handleError = (error: string | Error, title?: string): void => {
    const { newAlert } = this.props;
    if (!error) {
      return;
    }
    newAlert(
      "danger",
      title || "Playback error",
      typeof error === "object" ? error.message : error
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

  handleTokenError = async (
    error: Error | string,
    callbackFunction: () => void
  ): Promise<void> => {
    if (
      error &&
      typeof error === "object" &&
      error.message &&
      error.message === "Invalid token scopes."
    ) {
      this.handleAccountError();
    }
    try {
      const { apiService } = this.props;
      const userToken = await apiService.refreshSpotifyToken();
      this.setState({ accessToken: userToken }, () => {
        this.connectSpotifyPlayer(callbackFunction);
      });
    } catch (err) {
      this.handleError(err.message);
    }
  };

  handleAccountError = (): void => {
    const errorMessage = (
      <p>
        In order to play music, it is required that you link your Spotify
        Premium account.
        <br />
        Please try to{" "}
        <a href="/profile/connect-spotify" target="_blank">
          link for &quot;playing music&quot; feature
        </a>{" "}
        and refresh this page
      </p>
    );
    const { onAccountError } = this.props;
    if (onAccountError) {
      onAccountError(errorMessage);
    }
  };

  togglePlay = async (): Promise<void> => {
    try {
      await this.spotifyPlayer.togglePlay();
    } catch (error) {
      this.handleError(error.message);
    }
  };

  toggleDirection = (): void => {
    this.setState((prevState) => {
      const direction = prevState.direction === "down" ? "up" : "down";
      return { direction };
    });
  };

  disconnectSpotifyPlayer = (): void => {
    this.stopPlayerStateTimer();
    if (!this.spotifyPlayer) {
      return;
    }
    if (typeof this.spotifyPlayer.disconnect === "function") {
      this.spotifyPlayer.removeListener("initialization_error");
      this.spotifyPlayer.removeListener("authentication_error");
      this.spotifyPlayer.removeListener("account_error");
      this.spotifyPlayer.removeListener("playback_error");
      this.spotifyPlayer.removeListener("ready");
      this.spotifyPlayer.removeListener("player_state_changed");
      this.spotifyPlayer.disconnect();
    }
    this.spotifyPlayer = null;
    this.firstRun = true;
  };

  connectSpotifyPlayer = (callbackFunction?: () => void): void => {
    this.disconnectSpotifyPlayer();

    const { accessToken } = this.state;

    this.spotifyPlayer = new window.Spotify.Player({
      name: "ListenBrainz Player",
      getOAuthToken: (authCallback) => {
        authCallback(accessToken);
      },
      volume: 0.7, // Careful with this, now…
    });

    // Error handling
    this.spotifyPlayer.on("initialization_error", this.handleError);
    this.spotifyPlayer.on("authentication_error", this.handleTokenError);
    this.spotifyPlayer.on("account_error", this.handleAccountError);
    this.spotifyPlayer.on("playback_error", this.handleError);

    this.spotifyPlayer.addListener("ready", () => {
      if (callbackFunction) {
        callbackFunction();
      }
      this.startPlayerStateTimer();
      if (fixSpotifyPlayerStyleIssue) {
        fixSpotifyPlayerStyleIssue();
      }
    });

    this.spotifyPlayer.addListener(
      "player_state_changed",
      this.handlePlayerStateChanged
    );

    this.spotifyPlayer
      .connect()
      .then(
        async (success: any): Promise<Response> => {
          if (success) {
            return fetch(
              "https://api.spotify.com/v1/me/player/currently-playing",
              {
                method: "GET",
                headers: {
                  "Content-Type": "application/json",
                  Authorization: `Bearer ${accessToken}`,
                },
              }
            );
          }
          throw Error("Could not connect Web Playback SDK");
        }
      )
      .then((response: Response) => {
        if (response.status === 202 || response.status === 204) {
          // Failure, no response body.
          return null;
        }
        return response.json().then((innerResponse) => {
          if (innerResponse.error) {
            return this.handleError(innerResponse.error.message);
          }
          return this.handleSpotifyAPICurrentlyPlaying(innerResponse);
        });
      })
      .catch((error: Error) => {
        this.handleError(error.message);
      });
  };

  handleSpotifyAPICurrentlyPlaying = (currentlyPlaying: any): void => {
    if (currentlyPlaying.is_playing) {
      this.handleWarning(
        "Using Spotify on this page will interrupt your current playback",
        "Spotify player"
      );
    }
    this.setState({
      progressMs: currentlyPlaying.progress_ms,
      durationMs: currentlyPlaying.item && currentlyPlaying.item.duration_ms,
      currentSpotifyTrack: currentlyPlaying.item,
    });
  };

  startPlayerStateTimer = (): void => {
    this.playerStateTimerID = window.setInterval(() => {
      this.spotifyPlayer.getCurrentState().then(this.handlePlayerStateChanged);
    }, 500);
  };

  stopPlayerStateTimer = (): void => {
    if (this.playerStateTimerID) {
      window.clearInterval(this.playerStateTimerID);
    }
    this.playerStateTimerID = null;
  };

  handlePlayerStateChanged = (state: SpotifyPlayerSDKState): void => {
    if (!state) {
      return;
    }
    const {
      paused,
      position,
      duration,
      track_window: { current_track },
    } = state;

    if (paused) {
      this.stopPlayerStateTimer();
    } else if (!this.playerStateTimerID) {
      this.startPlayerStateTimer();
    }
    // How do we accurately detect the end of a song?
    // From https://github.com/spotify/web-playback-sdk/issues/35#issuecomment-469834686
    if (position === 0 && paused === true) {
      // Track finished, play next track
      this.debouncedPlayNextTrack();
      return;
    }
    this.setState({
      progressMs: position,
      durationMs: duration,
      currentSpotifyTrack: current_track || {},
      playerPaused: paused,
    });
    if (this.firstRun) {
      this.firstRun = false;
    }
  };

  getAlbumArt = (): JSX.Element | null => {
    const { currentSpotifyTrack } = this.state;
    if (
      !currentSpotifyTrack ||
      !currentSpotifyTrack.album ||
      !Array.isArray(currentSpotifyTrack.album.images)
    ) {
      return null;
    }
    const sortedImages = currentSpotifyTrack.album.images.sort(
      (a: SpotifyImage, b: SpotifyImage) => (a.height > b.height ? -1 : 1)
    );
    return (
      sortedImages[0] && (
        <img
          alt="coverart"
          className="img-responsive"
          src={sortedImages[0].url}
        />
      )
    );
  };

  render() {
    const {
      playerPaused,
      direction,
      currentSpotifyTrack,
      progressMs,
      durationMs,
    } = this.state;
    return (
      <div>
        <PlaybackControls
          playPreviousTrack={this.playPreviousTrack}
          playNextTrack={this.playNextTrack}
          togglePlay={this.firstRun ? this.playNextTrack : this.togglePlay}
          playerPaused={playerPaused}
          toggleDirection={this.toggleDirection}
          direction={direction}
          trackName={currentSpotifyTrack.name}
          artistName={
            currentSpotifyTrack.artists &&
            currentSpotifyTrack.artists
              .map((artist: SpotifyArtist) => artist.name)
              .join(", ")
          }
          progressMs={progressMs}
          durationMs={durationMs}
        >
          {this.getAlbumArt()}
        </PlaybackControls>
      </div>
    );
  }
}
