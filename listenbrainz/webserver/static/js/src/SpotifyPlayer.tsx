/* eslint-disable no-underscore-dangle */
import * as React from "react";
import {
  isEqual as _isEqual,
  get as _get,
  has as _has,
  debounce as _debounce,
} from "lodash";
import { searchForSpotifyTrack, loadScriptAsync } from "./utils";
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
  currentSpotifyTrack?: SpotifyTrack;
  durationMs: number;
  trackWindow?: SpotifyPlayerTrackWindow;
  device_id?: string;
};

export default class SpotifyPlayer
  extends React.Component<SpotifyPlayerProps, SpotifyPlayerState>
  implements DataSourceType {
  static hasPermissions = (spotifyUser: SpotifyUser) => {
    const { access_token: accessToken, permission } = spotifyUser;
    if (!accessToken || !permission) {
      return false;
    }
    const scopes = permission.split(" ");
    const requiredScopes = [
      "streaming",
      "user-read-email",
      "user-read-private",
    ];
    for (let i = 0; i < requiredScopes.length; i += 1) {
      if (!scopes.includes(requiredScopes[i])) {
        return false;
      }
    }
    return true;
  };

  spotifyPlayer?: SpotifyPlayerType;
  debouncedOnTrackEnd: () => void;

  constructor(props: SpotifyPlayerProps) {
    super(props);
    this.state = {
      accessToken: props.spotifyUser.access_token || "",
      durationMs: 0,
    };

    this.debouncedOnTrackEnd = _debounce(props.onTrackEnd, 500, {
      leading: true,
      trailing: false,
    });

    // Do an initial check of the spotify token permissions (scopes) before loading the SDK library
    if (SpotifyPlayer.hasPermissions(props.spotifyUser)) {
      window.onSpotifyWebPlaybackSDKReady = this.connectSpotifyPlayer;
      loadScriptAsync(document, "https://sdk.scdn.co/spotify-player.js");
    } else {
      this.handleAccountError();
    }
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

  searchAndPlayTrack = async (listen: Listen | JSPFTrack): Promise<void> => {
    const trackName =
      _get(listen, "track_metadata.track_name") || _get(listen, "title");
    const artistName =
      _get(listen, "track_metadata.artist_name") || _get(listen, "creator");
    // Using the releaseName has paradoxically given worst search results, so we're going to ignore it for now
    const releaseName = ""; // _get(listen, "track_metadata.release_name");
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
    try {
      const track = await searchForSpotifyTrack(
        accessToken,
        trackName,
        artistName,
        releaseName
      );
      if (track?.uri) {
        this.playSpotifyURI(track.uri);
        return;
      }
      onTrackNotFound();
    } catch (errorObject) {
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
      handleError(errorObject);
    }
  };

  playSpotifyURI = async (
    spotifyURI: string,
    retryCount = 0
  ): Promise<void> => {
    const { accessToken, device_id } = this.state;
    const { handleError } = this.props;
    if (retryCount > 5) {
      handleError("Could not play Spotify track", "Playback error");
      return;
    }
    if (!this.spotifyPlayer || !device_id) {
      this.connectSpotifyPlayer(
        this.playSpotifyURI.bind(this, spotifyURI, retryCount + 1)
      );
      return;
    }
    try {
      const response = await fetch(
        `https://api.spotify.com/v1/me/player/play?device_id=${device_id}`,
        {
          method: "PUT",
          body: JSON.stringify({ uris: [spotifyURI] }),
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );
      let errorMessage;
      try {
        errorMessage = await response.json();
      } catch (err) {
        console.error(err);
      }
      if (response.status === 401) {
        // Handle token error and try again if fixed
        this.handleTokenError(
          response.statusText,
          this.playSpotifyURI.bind(this, spotifyURI, retryCount + 1)
        );
        return;
      }
      if (response.status === 403) {
        this.handleAccountError();
        return;
      }
      if (response.status === 404) {
        // Device not found
        // Wait a second, reconnect and try again
        await new Promise((resolve) => setTimeout(resolve, 1000));
        this.connectSpotifyPlayer(
          this.playSpotifyURI.bind(this, spotifyURI, retryCount + 1)
        );
        return;
      }
      if (!response.ok) {
        handleError(errorMessage || response);
      }
    } catch (error) {
      handleError(error);
    }
  };

  playListen = (listen: Listen | JSPFTrack): void => {
    if (_get(listen, "track_metadata.additional_info.spotify_id")) {
      this.playSpotifyURI(getSpotifyUriFromListen(listen as Listen));
    } else {
      this.searchAndPlayTrack(listen);
    }
  };

  togglePlay = (): void => {
    const { handleError } = this.props;
    this.spotifyPlayer.togglePlay().catch((error: Response) => {
      handleError(error);
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
        In order to play music with Spotify, you will need a Spotify Premium
        account linked to your ListenBrainz account.
        <br />
        Please try to{" "}
        <a href="/profile/connect-spotify" target="_blank">
          link for &quot;playing music&quot; feature
        </a>{" "}
        and refresh this page
      </p>
    );
    const { onInvalidateDataSource } = this.props;
    onInvalidateDataSource(this, errorMessage);
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

  handleSpotifyPlayerError = (error: {
    status: number;
    message: string;
    reason: string;
  }): void => {
    const { handleError } = this.props;
    handleError(
      {
        status: error.status,
        message: `${error.reason ? `${error.reason} - ` : ""}${error.message}`,
      },
      "Spotify player error"
    );
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
    this.spotifyPlayer.on(
      "initialization_error",
      this.handleSpotifyPlayerError
    );
    this.spotifyPlayer.on("authentication_error", this.handleTokenError);
    this.spotifyPlayer.on("account_error", this.handleAccountError);
    this.spotifyPlayer.on("playback_error", this.handleSpotifyPlayerError);

    this.spotifyPlayer.addListener(
      "ready",
      ({ device_id }: { device_id: string }) => {
        this.setState({ device_id });
        if (callbackFunction) {
          callbackFunction();
        }
        if (fixSpotifyPlayerStyleIssue) {
          fixSpotifyPlayerStyleIssue();
        }
      }
    );

    this.spotifyPlayer.addListener(
      "player_state_changed",
      this.handlePlayerStateChanged
    );

    this.spotifyPlayer
      .connect()
      .then((success: boolean) => {
        if (!success) {
          throw Error("Could not connect Web Playback SDK");
        }
      })
      .catch((error: Error) => {
        handleError(error);
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
      (a: SpotifyImage, b: SpotifyImage) =>
        a?.height && b?.height && a.height > b.height ? -1 : 1
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
