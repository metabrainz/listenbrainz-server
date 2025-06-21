import * as React from "react";
import { get as _get, isString, throttle as _throttle } from "lodash";
import { Link } from "react-router";
import { faMusic } from "@fortawesome/free-solid-svg-icons";
import { DataSourceProps, DataSourceType } from "./BrainzPlayer";
import {
  getArtistName,
  getTrackName,
  searchForFunkwhaleTrack,
} from "../../utils/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { BrainzPlayerContext } from "./BrainzPlayerContext";
import { dataSourcesInfo } from "../../settings/brainzplayer/BrainzPlayerSettings";

export type FunkwhalePlayerState = {
  currentTrack?: FunkwhaleTrack;
};

export type FunkwhalePlayerProps = DataSourceProps & {
  refreshFunkwhaleToken: () => Promise<string>;
};

export default class FunkwhalePlayer
  extends React.Component<FunkwhalePlayerProps, FunkwhalePlayerState>
  implements DataSourceType {
  static contextType = GlobalAppContext;
  static hasPermissions = (funkwhaleUser?: FunkwhaleUser) => {
    return Boolean(funkwhaleUser?.access_token);
  };

  static isListenFromThisService(listen: Listen | JSPFTrack): boolean {
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    const musicService = _get(
      listen,
      "track_metadata.additional_info.music_service"
    );
    return (
      (isString(musicService) &&
        musicService.toLowerCase().includes("funkwhale")) ||
      (!!originURL && /funkwhale/.test(originURL)) ||
      Boolean(FunkwhalePlayer.getURLFromListen(listen))
    );
  }

  static getURLFromListen = (
    listen: Listen | JSPFTrack
  ): string | undefined => {
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (originURL && /funkwhale/.test(originURL)) {
      return originURL;
    }
    const funkwhaleId = _get(
      listen,
      "track_metadata.additional_info.funkwhale_id"
    );
    if (funkwhaleId) {
      return funkwhaleId;
    }
    return undefined;
  };

  public name = "funkwhale";
  public domainName = "funkwhale";
  public icon = faMusic; // FontAwesome fallback for player interface
  public iconColor = dataSourcesInfo.funkwhale.color;

  audioRef: React.RefObject<HTMLAudioElement>;
  updateProgressInterval?: NodeJS.Timeout;
  accessToken = "";
  retries = 0;
  declare context: React.ContextType<typeof GlobalAppContext>;

  debouncedOnTrackEnd: () => void;

  constructor(props: FunkwhalePlayerProps) {
    super(props);
    this.state = {
      currentTrack: undefined,
    };
    this.audioRef = React.createRef();

    this.debouncedOnTrackEnd = _throttle(this.onTrackEnd, 700, {
      leading: true,
      trailing: false,
    });
  }

  async componentDidMount(): Promise<void> {
    const { funkwhaleAuth: funkwhaleUser = undefined } = this.context;
    if (FunkwhalePlayer.hasPermissions(funkwhaleUser)) {
      this.accessToken = funkwhaleUser!.access_token;
      this.setupAudioListeners();
    }
  }

  componentDidUpdate(prevProps: DataSourceProps) {
    const { show } = this.props;
    if (prevProps.show !== show && show) {
      this.setupAudioListeners();
    }
  }

  componentWillUnmount(): void {
    this.cleanupAudioListeners();
    if (this.updateProgressInterval) {
      clearInterval(this.updateProgressInterval);
    }
  }

  setupAudioListeners = (): void => {
    const audioElement = this.audioRef.current;
    if (!audioElement) return;

    audioElement.addEventListener("loadedmetadata", this.onLoadedMetadata);
    audioElement.addEventListener("timeupdate", this.onTimeUpdate);
    audioElement.addEventListener("play", this.onPlay);
    audioElement.addEventListener("pause", this.onPause);
    audioElement.addEventListener("ended", this.onTrackEnd);
    audioElement.addEventListener("error", this.onError);
    audioElement.addEventListener("canplay", this.onCanPlay);
  };

  cleanupAudioListeners = (): void => {
    const audioElement = this.audioRef.current;
    if (!audioElement) return;

    audioElement.removeEventListener("loadedmetadata", this.onLoadedMetadata);
    audioElement.removeEventListener("timeupdate", this.onTimeUpdate);
    audioElement.removeEventListener("play", this.onPlay);
    audioElement.removeEventListener("pause", this.onPause);
    audioElement.removeEventListener("ended", this.onTrackEnd);
    audioElement.removeEventListener("error", this.onError);
    audioElement.removeEventListener("canplay", this.onCanPlay);
  };

  onLoadedMetadata = (): void => {
    const { onDurationChange } = this.props;
    const audioElement = this.audioRef.current;
    if (audioElement) {
      onDurationChange(audioElement.duration * 1000);
    }
  };

  onTimeUpdate = (): void => {
    const { onProgressChange } = this.props;
    const audioElement = this.audioRef.current;
    if (audioElement) {
      onProgressChange(audioElement.currentTime * 1000);
    }
  };

  onPlay = (): void => {
    const { onPlayerPausedChange } = this.props;
    onPlayerPausedChange(false);
  };

  onPause = (): void => {
    const { onPlayerPausedChange } = this.props;
    onPlayerPausedChange(true);
  };

  onTrackEnd = (): void => {
    const { onTrackEnd } = this.props;
    onTrackEnd();
  };

  onError = (event: Event): void => {
    const { handleError } = this.props;
    const audioElement = event.target as HTMLAudioElement;
    let errorMessage = "Audio playback error";

    if (audioElement.error) {
      switch (audioElement.error.code) {
        case audioElement.error.MEDIA_ERR_ABORTED:
          errorMessage = "Audio playback was aborted";
          break;
        case audioElement.error.MEDIA_ERR_NETWORK:
          errorMessage = "Network error occurred during audio playback";
          break;
        case audioElement.error.MEDIA_ERR_DECODE:
          errorMessage = "Audio decoding error";
          break;
        case audioElement.error.MEDIA_ERR_SRC_NOT_SUPPORTED:
          errorMessage = "Audio format not supported";
          break;
        default:
          errorMessage = "Unknown audio error";
      }
    }

    handleError(errorMessage, "Funkwhale playback error");
  };

  onCanPlay = (): void => {
    // Audio is ready to play
    const { currentTrack } = this.state;
    if (currentTrack) {
      this.updateTrackInfo();
    }
  };

  updateTrackInfo = (): void => {
    const { onTrackInfoChange } = this.props;
    const { currentTrack } = this.state;

    if (!currentTrack) return;

    const artwork: MediaImage[] = [];
    if (currentTrack.album?.cover?.large) {
      artwork.push({
        src: currentTrack.album.cover.large,
        sizes: "500x500",
        type: "image/jpeg",
      });
    }

    onTrackInfoChange(
      currentTrack.title,
      currentTrack.listen_url || "",
      currentTrack.artist?.name || "",
      currentTrack.album?.title || "",
      artwork
    );
  };

  playListen = async (listen: Listen | JSPFTrack): Promise<void> => {
    const listenFromFunkwhale = FunkwhalePlayer.isListenFromThisService(listen);

    if (listenFromFunkwhale) {
      const funkwhaleURL = FunkwhalePlayer.getURLFromListen(listen);
      if (funkwhaleURL) {
        await this.playFunkwhaleURL(funkwhaleURL);
        return;
      }
    }

    // If not a direct Funkwhale URL, search for the track
    await this.searchAndPlayTrack(listen);
  };

  playFunkwhaleURL = async (url: string): Promise<void> => {
    const audioElement = this.audioRef.current;
    if (!audioElement) return;

    try {
      // Extract track ID from URL if needed
      const trackId = this.extractTrackIdFromURL(url);
      if (trackId) {
        const track = await this.fetchTrackInfo(trackId);
        if (track && track.listen_url) {
          audioElement.src = track.listen_url;
          this.setState({ currentTrack: track });
          await audioElement.play();
        }
      } else {
        // Direct audio URL
        audioElement.src = url;
        await audioElement.play();
      }
    } catch (error) {
      const { handleError } = this.props;
      handleError(
        error.message || "Failed to play Funkwhale track",
        "Funkwhale Error"
      );
    }
  };

  extractTrackIdFromURL = (url: string): string | null => {
    // Extract track ID from various Funkwhale URL formats
    const trackMatch = url.match(/\/tracks\/(\d+)/);
    if (trackMatch) {
      return trackMatch[1];
    }
    return null;
  };

  fetchTrackInfo = async (trackId: string): Promise<FunkwhaleTrack | null> => {
    if (!this.accessToken) return null;

    try {
      const instanceURL = this.getFunkwhaleInstanceURL();
      const response = await fetch(`${instanceURL}/api/v1/tracks/${trackId}/`, {
        headers: {
          Authorization: `Bearer ${this.accessToken}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      // Log the error for debugging
      return null;
    }
  };

  getFunkwhaleInstanceURL = (): string => {
    // This should be configurable per user or globally
    // For now, return a default or get from context
    const { funkwhaleAuth: funkwhaleUser = undefined } = this.context;
    return funkwhaleUser?.instance_url || "https://demo.funkwhale.audio";
  };

  searchAndPlayTrack = async (listen: Listen | JSPFTrack): Promise<void> => {
    const trackName = getTrackName(listen);
    const artistName = getArtistName(listen);
    const { handleError, handleWarning, onTrackNotFound } = this.props;

    if (!trackName && !artistName) {
      handleWarning(
        "We are missing a track title and artist name to search on Funkwhale",
        "Not enough info to search on Funkwhale"
      );
      onTrackNotFound();
      return;
    }

    try {
      const track = await searchForFunkwhaleTrack(
        this.accessToken,
        this.getFunkwhaleInstanceURL(),
        trackName,
        artistName
      );

      if (track && track.listen_url) {
        this.setState({ currentTrack: track });
        const audioElement = this.audioRef.current;
        if (audioElement) {
          audioElement.src = track.listen_url;
          await audioElement.play();
        }
        return;
      }
      onTrackNotFound();
    } catch (errorObject) {
      if (errorObject.status === 401) {
        await this.handleTokenError(
          errorObject.message,
          this.searchAndPlayTrack.bind(this, listen)
        );
        return;
      }
      handleError(
        errorObject.message ?? errorObject,
        "Error searching on Funkwhale"
      );
    }
  };

  handleTokenError = async (
    error: Error | string,
    callbackFunction: () => void
  ): Promise<void> => {
    const { refreshFunkwhaleToken, onInvalidateDataSource } = this.props;
    const { funkwhaleAuth: funkwhaleUser = undefined } = this.context;

    if (!funkwhaleUser?.instance_url) {
      onInvalidateDataSource(
        this as any,
        <span>
          Please{" "}
          <Link to="/settings/music-services/details/">
            re-connect your Funkwhale account
          </Link>
        </span>
      );
      return;
    }

    try {
      this.accessToken = await refreshFunkwhaleToken();
      callbackFunction();
    } catch (refreshError) {
      onInvalidateDataSource(
        this as any,
        <span>
          Please{" "}
          <Link to="/settings/music-services/details/">
            re-connect your Funkwhale account
          </Link>
        </span>
      );
    }
  };

  togglePlay = async (): Promise<void> => {
    const audioElement = this.audioRef.current;
    if (!audioElement) return;

    try {
      if (audioElement.paused) {
        await audioElement.play();
      } else {
        audioElement.pause();
      }
    } catch (error) {
      const { handleError } = this.props;
      handleError(error.message, "Funkwhale playback error");
    }
  };

  seekToPositionMs = (msTimecode: number): void => {
    const audioElement = this.audioRef.current;
    if (audioElement) {
      audioElement.currentTime = msTimecode / 1000;
    }
  };

  canSearchAndPlayTracks = (): boolean => {
    const { funkwhaleAuth: funkwhaleUser = undefined } = this.context;
    return FunkwhalePlayer.hasPermissions(funkwhaleUser);
  };

  datasourceRecordsListens = (): boolean => {
    return false; // will record listens to ListenBrainz later
  };

  render() {
    const { show, volume = 100 } = this.props;

    return (
      <div className={`funkwhale-player ${show ? "" : "hidden"}`}>
        <audio ref={this.audioRef} crossOrigin="anonymous" preload="metadata">
          <track kind="captions" />
        </audio>
      </div>
    );
  }
}
