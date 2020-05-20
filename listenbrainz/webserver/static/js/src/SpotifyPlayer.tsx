import * as React from "react";
import {
  isEqual as _isEqual,
  get as _get,
  has as _has,
  debounce as _debounce,
} from "lodash";
import { searchForSpotifyTrack } from "./utils";
import { DataSourceType, DataSourceProps } from "./BrainzPlayer";

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

type SpotifyPlayerProps = DataSourceProps & {
  spotifyUser: SpotifyUser;
  refreshSpotifyToken: () => Promise<string>;
};

type SpotifyPlayerState = {
  accessToken: string;
  permission: SpotifyPermission;
  currentSpotifyTrack?: SpotifyTrack;
  durationMs: number;
  trackWindow?: SpotifyPlayerTrackWindow;
};

export default class SpotifyPlayer
  extends React.Component<SpotifyPlayerProps, SpotifyPlayerState>
  implements DataSourceType {
  spotifyPlayer?: SpotifyPlayerType;

  debouncedOnTrackEnd: () => void;

  constructor(props: SpotifyPlayerProps) {
    super(props);
    this.state = {
      accessToken: props.spotifyUser.access_token,
      permission: props.spotifyUser.permission,
      durationMs: 0,
    };

    this.debouncedOnTrackEnd = _debounce(props.onTrackEnd, 500, {
      leading: true,
      trailing: false,
    });

    const { accessToken, permission } = this.state;

    // Do an initial check of the spotify token permissions (scopes) before loading the SDK library
    this.checkSpotifyToken(accessToken, permission).then((success) => {
      if (success) {
        window.onSpotifyWebPlaybackSDKReady = this.connectSpotifyPlayer;
        const spotifyPlayerSDKLib = require("../lib/spotify-player-sdk-1.7.1"); // eslint-disable-line global-require
      }
    });
  }

  componentDidUpdate(prevProps: DataSourceProps) {
    const { show } = this.props;
    if (prevProps.show === true && show === false) {
      this.stopAndClear();
    }
  }

  componentWillUnmount(): void {
    this.disconnectSpotifyPlayer();
  }

  searchAndPlayTrack = (listen: Listen): void => {
    const trackName = _get(listen, "track_metadata.track_name");
    const artistName = _get(listen, "track_metadata.artist_name");
    // Using the releaseName has paradoxically given worst search results, so we're going to ignor it for now
    // const releaseName = _get(listen, "track_metadata.release_name");
    const releaseName = "";
    const {
      handleError,
      handleWarning,
      handleSuccess,
      onTrackNotFound,
    } = this.props;
    if (!trackName) {
      handleWarning("Not enough info to search on Spotify");
      onTrackNotFound();
    }
    const { accessToken } = this.state;

    searchForSpotifyTrack(accessToken, trackName, artistName, releaseName)
      .then((track) => {
        // Track should be a Spotify track object:
        // https://developer.spotify.com/documentation/web-api/reference/object-model/#track-object-full
        if (_has(track, "name") && _has(track, "id") && _has(track, "uri")) {
          handleSuccess(
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
        // handleWarning("Could not find track on Spotify");
        onTrackNotFound();
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
        handleError(errorObject.message);
      });
  };

  playSpotifyURI = (spotifyURI: string): void => {
    if (!this.spotifyPlayer) {
      this.connectSpotifyPlayer(this.playSpotifyURI.bind(this, spotifyURI));
      return;
    }
    const { accessToken } = this.state;
    const { handleError } = this.props;
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
          handleError(response.statusText);
        }
      })
      .catch((error) => {
        handleError(error.message);
      });
  };

  checkSpotifyToken = async (
    accessToken?: string,
    permission?: string
  ): Promise<boolean> => {
    const { onInvalidateDataSource, handleError } = this.props;
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
          onInvalidateDataSource("Permission to play songs not granted");
          return false;
        }
      }
      return true;
    } catch (error) {
      handleError(error);
      return false;
    }
  };

  playListen = (listen: Listen): void => {
    if (_get(listen, "track_metadata.additional_info.spotify_id")) {
      this.playSpotifyURI(getSpotifyUriFromListen(listen));
    } else {
      this.searchAndPlayTrack(listen);
    }
  };

  togglePlay = (): void => {
    const { handleError } = this.props;
    this.spotifyPlayer.togglePlay().catch((error: Error) => {
      handleError(error.message);
    });
  };

  stopAndClear = (): void => {
    this.setState({ currentSpotifyTrack: undefined });
    if (this.spotifyPlayer) {
      this.spotifyPlayer.pause();
    }
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
    const { refreshSpotifyToken, onTrackNotFound } = this.props;
    try {
      const userToken = await refreshSpotifyToken();
      this.setState({ accessToken: userToken }, () => {
        this.connectSpotifyPlayer(callbackFunction);
      });
    } catch (err) {
      const { handleError } = this.props;
      handleError(err.message, "Spotify error");
      onTrackNotFound();
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
    const { onInvalidateDataSource } = this.props;
    if (onInvalidateDataSource) {
      onInvalidateDataSource(errorMessage);
    }
  };

  seekToPositionMs = (msTimecode: number): void => {
    this.spotifyPlayer.seek(msTimecode);
  };

  disconnectSpotifyPlayer = (): void => {
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
  };

  connectSpotifyPlayer = (callbackFunction?: () => void): void => {
    this.disconnectSpotifyPlayer();

    const { accessToken } = this.state;

    if (!window.Spotify) {
      setTimeout(this.connectSpotifyPlayer.bind(this, callbackFunction), 1000);
      return;
    }

    this.spotifyPlayer = new window.Spotify.Player({
      name: "ListenBrainz Player",
      getOAuthToken: (authCallback) => {
        authCallback(accessToken);
      },
      volume: 0.7, // Careful with this, now…
    });

    const { handleError } = this.props;
    // Error handling
    this.spotifyPlayer.on("initialization_error", handleError);
    this.spotifyPlayer.on("authentication_error", this.handleTokenError);
    this.spotifyPlayer.on("account_error", this.handleAccountError);
    this.spotifyPlayer.on("playback_error", handleError);

    this.spotifyPlayer.addListener("ready", () => {
      if (callbackFunction) {
        callbackFunction();
      }
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
            return handleError(innerResponse.error.message);
          }
          return this.handleSpotifyAPICurrentlyPlaying(innerResponse);
        });
      })
      .catch((error: Error) => {
        handleError(error.message);
      });
  };

  handleSpotifyAPICurrentlyPlaying = (currentlyPlaying: any): void => {
    const { handleWarning, onProgressChange, onDurationChange } = this.props;
    const { durationMs } = this.state;
    if (currentlyPlaying.is_playing) {
      handleWarning(
        "Using Spotify on this page will interrupt your current playback",
        "Spotify player"
      );
    }

    onProgressChange(currentlyPlaying.progress_ms);

    const newDurationMs = _get(currentlyPlaying, "item.duration_ms", null);
    if (newDurationMs !== null && newDurationMs !== durationMs) {
      onDurationChange(newDurationMs);
    }
    this.setState({
      durationMs: newDurationMs,
      currentSpotifyTrack: currentlyPlaying.item,
    });
  };

  handlePlayerStateChanged = (playerState: SpotifyPlayerSDKState): void => {
    const { show } = this.props;
    if (!playerState || !show) {
      return;
    }
    const {
      paused,
      position,
      duration,
      track_window: { current_track },
    } = playerState;

    const { currentSpotifyTrack, durationMs } = this.state;
    const { playerPaused } = this.props;
    const {
      onPlayerPausedChange,
      onProgressChange,
      onDurationChange,
    } = this.props;

    if (paused !== playerPaused) {
      onPlayerPausedChange(paused);
    }

    // How do we accurately detect the end of a song?
    // From https://github.com/spotify/web-playback-sdk/issues/35#issuecomment-469834686
    if (position === 0 && paused === true) {
      // Track finished, play next track
      this.debouncedOnTrackEnd();
      return;
    }

    if (!_isEqual(_get(currentSpotifyTrack, "id"), current_track.id)) {
      const { onTrackInfoChange } = this.props;

      const artists = current_track.artists
        .map((artist: SpotifyArtist) => artist.name)
        .join(", ");
      onTrackInfoChange(current_track.name, artists);

      this.setState({
        durationMs: duration,
        currentSpotifyTrack: current_track,
      });
      return;
    }

    onProgressChange(position);

    if (duration !== durationMs) {
      onDurationChange(duration);
      this.setState({
        durationMs: duration,
      });
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
    const { show } = this.props;
    if (!show) {
      return null;
    }
    return <div>{this.getAlbumArt()}</div>;
  }
}
