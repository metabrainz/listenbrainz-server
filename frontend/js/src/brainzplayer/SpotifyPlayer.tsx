/* eslint-disable no-underscore-dangle */
import * as React from "react";
import {
  isEqual as _isEqual,
  get as _get,
  has as _has,
  debounce as _debounce,
  isString,
  has,
} from "lodash";
import { faSpotify } from "@fortawesome/free-brands-svg-icons";
import {
  searchForSpotifyTrack,
  loadScriptAsync,
  getTrackName,
  getArtistName,
} from "../utils/utils";
import { DataSourceType, DataSourceProps } from "./BrainzPlayer";

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

export type SpotifyPlayerProps = DataSourceProps & {
  spotifyUser?: SpotifyUser;
  refreshSpotifyToken: () => Promise<string>;
};

export type SpotifyPlayerState = {
  currentSpotifyTrack?: SpotifyTrack;
  durationMs: number;
  trackWindow?: SpotifyPlayerTrackWindow;
  device_id?: string;
};

export default class SpotifyPlayer
  extends React.Component<SpotifyPlayerProps, SpotifyPlayerState>
  implements DataSourceType {
  static hasPermissions = (spotifyUser?: SpotifyUser) => {
    if (!spotifyUser) {
      return false;
    }
    const { access_token: accessToken, permission } = spotifyUser;
    if (!accessToken || !permission) {
      return false;
    }
    const scopes = permission;
    const requiredScopes = [
      "streaming",
      "user-read-email",
      "user-read-private",
    ] as Array<SpotifyPermission>;
    for (let i = 0; i < requiredScopes.length; i += 1) {
      if (!scopes.includes(requiredScopes[i])) {
        return false;
      }
    }
    return true;
  };

  static isListenFromThisService = (listen: Listen | JSPFTrack): boolean => {
    // Retro-compatibility: listening_from has been deprecated in favor of music_service
    const listeningFrom = _get(
      listen,
      "track_metadata.additional_info.listening_from"
    );
    const musicService = _get(
      listen,
      "track_metadata.additional_info.music_service"
    );
    return (
      (isString(listeningFrom) && listeningFrom.toLowerCase() === "spotify") ||
      (isString(musicService) &&
        musicService.toLowerCase() === "spotify.com") ||
      Boolean(SpotifyPlayer.getURLFromListen(listen))
    );
  };

  static getURLFromListen(listen: Listen | JSPFTrack): string | undefined {
    const spotifyId = _get(listen, "track_metadata.additional_info.spotify_id");
    if (spotifyId) {
      return spotifyId;
    }
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (originURL && /open\.spotify\.com\/track\//.test(originURL)) {
      return originURL;
    }
    return undefined;
  }

  public name = "spotify";
  public domainName = "spotify.com";
  public icon = faSpotify;
  // Saving the access token outside of React state , we do not need it for any rendering purposes
  // and it simplifies some of the closure issues we've had with old tokens.
  private accessToken = "";
  private authenticationRetries = 0;
  spotifyPlayer?: SpotifyPlayerType;
  debouncedOnTrackEnd: () => void;

  constructor(props: SpotifyPlayerProps) {
    super(props);

    this.accessToken = props.spotifyUser?.access_token || "";
    this.state = {
      durationMs: 0,
    };

    this.debouncedOnTrackEnd = _debounce(props.onTrackEnd, 700, {
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

  static getSpotifyTrackIDFromListen(listen: Listen | JSPFTrack): string {
    const spotifyId = SpotifyPlayer.getURLFromListen(listen);
    if (!spotifyId) {
      return "";
    }
    const spotifyTrack = spotifyId.split(
      "https://open.spotify.com/track/"
    )?.[1];
    return spotifyTrack;
  }

  static getSpotifyUriFromListen(listen: Listen | JSPFTrack): string {
    const spotifyTrack = SpotifyPlayer.getSpotifyTrackIDFromListen(listen);
    // spotifyTrack could be undefined
    if (!spotifyTrack) {
      return "";
    }
    return `spotify:track:${spotifyTrack}`;
  }

  searchAndPlayTrack = async (listen: Listen | JSPFTrack): Promise<void> => {
    const trackName = getTrackName(listen);
    const artistName = getArtistName(listen);
    // Using the releaseName has paradoxically given worst search results,
    // so we're only using it when track name isn't provided (for example for an album search)
    const releaseName = trackName
      ? ""
      : _get(listen, "track_metadata.release_name");
    const {
      handleError,
      handleWarning,
      handleSuccess,
      onTrackNotFound,
    } = this.props;
    if (!trackName && !artistName && !releaseName) {
      handleWarning("Not enough info to search on Spotify");
      onTrackNotFound();
    }

    try {
      const track = await searchForSpotifyTrack(
        this.accessToken,
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
      if (!has(errorObject, "status")) {
        handleError(errorObject.message ?? errorObject);
      }
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
      }
    }
  };

  playSpotifyURI = async (
    spotifyURI: string,
    retryCount = 0
  ): Promise<void> => {
    const { device_id } = this.state;
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
            Authorization: `Bearer ${this.accessToken}`,
          },
        }
      );
      let errorObject;
      if (response.ok) {
        return;
      }
      try {
        errorObject = await response.json();
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error(err);
      }
      const status = errorObject?.status ?? response.status;
      if (status === 401) {
        // Handle token error and try again if fixed
        this.handleTokenError(
          errorObject ?? response.statusText,
          this.playSpotifyURI.bind(this, spotifyURI, retryCount + 1)
        );
        return;
      }
      if (status === 403) {
        this.handleAccountError();
        return;
      }
      if (status === 404 || status >= 500) {
        // Device not found or server error on the Spotify API
        // Wait a second, recreate the local Spotify player and try again
        await new Promise((resolve) => {
          setTimeout(resolve, 1000);
        });
        this.connectSpotifyPlayer(
          this.playSpotifyURI.bind(this, spotifyURI, retryCount + 1)
        );
        return;
      }
      // catch-all
      handleError(errorObject?.message ?? response);
    } catch (error) {
      handleError(error.message);
    }
  };

  canSearchAndPlayTracks = (): boolean => {
    const { spotifyUser } = this.props;
    return SpotifyPlayer.hasPermissions(spotifyUser);
  };

  datasourceRecordsListens = (): boolean => {
    // Starting 2022 we realized tracks played through BrainzPlayer + Spotify
    // don't appear in the Spotify listening history anymore
    // and consequently don't appear in LB user's listens.
    // From here onwards we submit listens ourselves and hope there are no duplicates…
    return false;
  };

  playListen = (listen: Listen | JSPFTrack): void => {
    const { show } = this.props;
    if (!show) {
      return;
    }
    if (SpotifyPlayer.getURLFromListen(listen)) {
      this.playSpotifyURI(
        SpotifyPlayer.getSpotifyUriFromListen(listen as Listen)
      );
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
    error: Error | string | Spotify.Error,
    callbackFunction: () => void
  ): Promise<void> => {
    if (!isString(error) && error?.message === "Invalid token scopes.") {
      this.handleAccountError();
      return;
    }
    const { onTrackNotFound } = this.props;
    if (this.authenticationRetries > 5) {
      const { handleError } = this.props;
      handleError(
        isString(error) ? error : error?.message,
        "Spotify token error"
      );
      onTrackNotFound();
      return;
    }
    this.authenticationRetries += 1;
    // Reconnect spotify player; user token will be refreshed in the process
    this.connectSpotifyPlayer(callbackFunction);
  };

  handleAccountError = (): void => {
    const errorMessage = (
      <p>
        In order to play music with Spotify, you will need a Spotify Premium
        account linked to your ListenBrainz account.
        <br />
        Please try to{" "}
        <a href="/profile/music-services/details/" target="_blank">
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

    if (!window.Spotify) {
      setTimeout(this.connectSpotifyPlayer.bind(this, callbackFunction), 1000);
      return;
    }
    const { refreshSpotifyToken } = this.props;

    this.spotifyPlayer = new window.Spotify.Player({
      name: "ListenBrainz Player",
      getOAuthToken: async (authCallback) => {
        try {
          const userToken = await refreshSpotifyToken();
          this.accessToken = userToken;
          this.authenticationRetries = 0;
          authCallback(userToken);
        } catch (error) {
          handleError(error, "Error connecting to Spotify");
          setTimeout(
            this.connectSpotifyPlayer.bind(this, callbackFunction),
            1000
          );
        }
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
      track_window: { current_track, previous_tracks },
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

    if (!current_track) {
      // Assume we got a state update from another device, and don't try to do anything
      // which could overwrite the user's action (like playing next song with this 'device')
      return;
    }
    // How do we accurately detect the end of a song?
    // From https://github.com/spotify/web-playback-sdk/issues/35#issuecomment-509159445
    // If the current_track (i.e. just finished track) also appears in previous_tracks, we're at the end of that track
    if (
      position === 0 &&
      paused === true &&
      previous_tracks?.findIndex((track) => track.id === current_track.id) !==
        -1
    ) {
      // Track finished or skipped, play next track
      this.debouncedOnTrackEnd();
      return;
    }

    if (!_isEqual(_get(currentSpotifyTrack, "id"), current_track.id)) {
      const { onTrackInfoChange } = this.props;

      const artists = current_track.artists
        .map((artist: SpotifyArtist) => artist.name)
        .join(", ");
      onTrackInfoChange(
        current_track.name,
        `https://open.spotify.com/track/${current_track.id}`,
        artists,
        current_track.album?.name,
        current_track.album.images
          .filter((image) => image.url)
          .map((image) => {
            const mediaImage: MediaImage = {
              src: image.url,
            };
            if (image.width && image.height) {
              mediaImage.sizes = `${image.width}x${image.height}`;
            }
            return mediaImage;
          })
      );

      this.setState({
        durationMs: duration,
        currentSpotifyTrack: current_track ?? undefined,
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
