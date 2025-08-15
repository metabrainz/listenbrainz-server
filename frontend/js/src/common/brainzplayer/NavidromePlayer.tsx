import * as React from "react";
import { get as _get, isString, throttle as _throttle } from "lodash";
import { Link } from "react-router";
import { faMusic } from "@fortawesome/free-solid-svg-icons";
import { faNavidrome } from "../icons/faNavidrome";
import { DataSourceProps, DataSourceType } from "./BrainzPlayer";
import {
  getArtistName,
  getTrackName,
  searchForNavidromeTrack,
} from "../../utils/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { dataSourcesInfo } from "../../settings/brainzplayer/BrainzPlayerSettings";

export type NavidromePlayerState = {
  currentTrack?: NavidromeTrack;
};

export type NavidromePlayerProps = DataSourceProps & {
  refreshNavidromeToken: () => Promise<string>;
};

export default class NavidromePlayer
  extends React.Component<NavidromePlayerProps, NavidromePlayerState>
  implements DataSourceType {
  static contextType = GlobalAppContext;
  static hasPermissions = (navidromeUser?: NavidromeUser) => {
    return Boolean(
      navidromeUser?.encrypted_password && navidromeUser?.instance_url
    );
  };

  static isListenFromThisService(listen: Listen | JSPFTrack): boolean {
    const musicService = _get(
      listen,
      "track_metadata.additional_info.music_service"
    );
    return (
      (isString(musicService) &&
        musicService.toLowerCase().includes("navidrome")) ||
      Boolean(NavidromePlayer.getURLFromListen(listen))
    );
  }

  static getURLFromListen = (
    listen: Listen | JSPFTrack
  ): string | undefined => {
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (originURL && /navidrome/.test(originURL)) {
      return originURL;
    }
    const navidromeId = _get(
      listen,
      "track_metadata.additional_info.navidrome_id"
    );
    if (navidromeId) {
      return navidromeId;
    }
    return undefined;
  };

  public name = "navidrome";
  public domainName = "navidrome";
  public icon = faNavidrome;
  public iconColor = dataSourcesInfo.navidrome.color;

  audioRef: React.RefObject<HTMLAudioElement>;
  updateProgressInterval?: NodeJS.Timeout;
  accessToken = "";
  declare context: React.ContextType<typeof GlobalAppContext>;

  debouncedOnTrackEnd: () => void;

  constructor(props: NavidromePlayerProps) {
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
    const { navidromeAuth: navidromeUser = undefined } = this.context;
    if (NavidromePlayer.hasPermissions(navidromeUser)) {
      this.accessToken = navidromeUser!.encrypted_password!;
      this.setupAudioListeners();
    }
    this.updateVolume();
  }

  componentDidUpdate(prevProps: DataSourceProps) {
    const { show, volume } = this.props;
    if (prevProps.show !== show) {
      if (show) {
        this.setupAudioListeners();
      } else {
        this.pauseAudio();
      }
    }
    if (prevProps.volume !== volume) {
      this.updateVolume();
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

    this.updateVolume();
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
      const errorCode = audioElement.error.code;
      const errorMessages: Record<number, string> = {
        [audioElement.error.MEDIA_ERR_ABORTED]: "Audio playback was aborted",
        [audioElement.error.MEDIA_ERR_NETWORK]: "Network error during playback",
        [audioElement.error.MEDIA_ERR_DECODE]: "Audio decoding error",
        [audioElement.error.MEDIA_ERR_SRC_NOT_SUPPORTED]:
          "Audio format not supported",
      };
      errorMessage = errorMessages[errorCode] || "Unknown audio error";
    }

    handleError(errorMessage, "Navidrome playback error");
  };

  onCanPlay = (): void => {
    const { currentTrack } = this.state;
    if (currentTrack) {
      this.updateTrackInfo();
    }
  };

  getTrackArtworkUrl = (track?: NavidromeTrack): string | null => {
    if (!track?.albumId) return null;

    // Navidrome uses getCoverArt endpoint for artwork
    const instanceURL = this.getNavidromeInstanceURL();
    const authParams = this.getAuthParams();
    return `${instanceURL}/rest/getCoverArt?id=${track.albumId}&${authParams}`;
  };

  updateTrackInfo = (): void => {
    const { onTrackInfoChange } = this.props;
    const { currentTrack } = this.state;

    if (!currentTrack) return;

    const artworkUrl = this.getTrackArtworkUrl(currentTrack);
    const artwork: MediaImage[] = artworkUrl
      ? [
          {
            src: artworkUrl,
            sizes: "500x500",
            type: "image/jpeg",
          },
        ]
      : [];

    onTrackInfoChange(
      currentTrack.title,
      currentTrack.path || "",
      currentTrack.artist || "",
      currentTrack.album || "",
      artwork
    );
  };

  playListen = async (listen: Listen | JSPFTrack): Promise<void> => {
    const listenFromNavidrome = NavidromePlayer.isListenFromThisService(listen);

    if (listenFromNavidrome) {
      const navidromeURL = NavidromePlayer.getURLFromListen(listen);
      if (navidromeURL) {
        await this.playNavidromeURL(navidromeURL);
        return;
      }
    }

    // If not a direct Navidrome URL, search for the track
    await this.searchAndPlayTrack(listen);
  };

  playNavidromeURL = async (url: string): Promise<void> => {
    const audioElement = this.audioRef.current;
    if (!audioElement) return;

    try {
      // Extract track ID from URL if needed
      const trackId = this.extractTrackIdFromURL(url);
      if (trackId) {
        const track = await this.fetchTrackInfo(trackId);
        if (track) {
          // Get authenticated audio URL using Navidrome's stream endpoint
          const streamUrl = this.getNavidromeStreamUrl(track.id);
          this.setAudioSrc(audioElement, streamUrl);
          this.setState({ currentTrack: track });
          await audioElement.play();
        } else {
          throw new Error("Track not found on Navidrome server");
        }
      } else {
        // Direct audio URL - construct stream URL if possible
        const streamUrl = this.constructStreamUrlFromPath(url);
        if (streamUrl) {
          this.setAudioSrc(audioElement, streamUrl);
          await audioElement.play();
        } else {
          throw new Error("Unable to construct stream URL for Navidrome track");
        }
      }
    } catch (error) {
      const { handleError } = this.props;
      handleError(
        error.message || "Failed to play Navidrome track",
        "Navidrome Error"
      );
    }
  };

  extractTrackIdFromURL = (url: string): string | null => {
    // Navidrome URLs might have different patterns
    const trackMatch = url.match(/\/song\/([^/]+)/);
    if (trackMatch) return trackMatch[1];

    const idMatch = url.match(/id=([^&]+)/);
    return idMatch ? idMatch[1] : null;
  };

  fetchTrackInfo = async (trackId: string): Promise<NavidromeTrack | null> => {
    if (!this.accessToken) return null;

    try {
      const instanceURL = this.getNavidromeInstanceURL();
      const authParams = this.getAuthParams();

      const response = await fetch(
        `${instanceURL}/rest/getSong?id=${trackId}&${authParams}`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data["subsonic-response"]?.song || null;
    } catch (error) {
      return null;
    }
  };

  getNavidromeInstanceURL = (): string => {
    const { navidromeAuth: navidromeUser = undefined } = this.context;
    return navidromeUser?.instance_url || "";
  };

  getAuthParams = (): string => {
    const { navidromeAuth: navidromeUser = undefined } = this.context;
    if (!navidromeUser) return "";

    const { username = "", encrypted_password = "", salt = "" } = navidromeUser;

    if (!encrypted_password || !username) return "";

    // Use the fresh salt and hash provided by backend
    // Backend generates: MD5(password + salt) and fresh random salt for each request
    const authSalt = salt || `${username}_listenbrainz_fallback`; // Fallback for compatibility

    return `u=${encodeURIComponent(username)}&t=${encodeURIComponent(
      encrypted_password
    )}&s=${encodeURIComponent(authSalt)}&v=1.16.1&c=listenbrainz&f=json`;
  };

  getNavidromeStreamUrl = (trackId: string): string => {
    const instanceURL = this.getNavidromeInstanceURL();
    const authParams = this.getAuthParams();

    return `${instanceURL}/rest/stream?id=${trackId}&${authParams}`;
  };

  constructStreamUrlFromPath = (path: string): string | null => {
    // If the path looks like it might be a track ID, construct stream URL
    if (path && !path.includes("/")) {
      return this.getNavidromeStreamUrl(path);
    }
    return null;
  };

  searchAndPlayTrack = async (listen: Listen | JSPFTrack): Promise<void> => {
    const trackName = getTrackName(listen);
    const artistName = getArtistName(listen);
    const { handleError, handleWarning, onTrackNotFound } = this.props;

    if (!trackName && !artistName) {
      handleWarning(
        "We are missing a track title and artist name to search on Navidrome",
        "Not enough info to search on Navidrome"
      );
      onTrackNotFound();
      return;
    }

    try {
      const track = await searchForNavidromeTrack(
        this.getNavidromeInstanceURL(),
        this.getAuthParams(),
        trackName,
        artistName
      );

      if (track) {
        this.setState({ currentTrack: track });
        const audioElement = this.audioRef.current;
        if (audioElement) {
          const streamUrl = this.getNavidromeStreamUrl(track.id);
          this.setAudioSrc(audioElement, streamUrl);
          await audioElement.play();
          return;
        }
      }

      handleWarning(
        `"${trackName}" by ${artistName} is not available on your Navidrome server`,
        "Track not available on Navidrome"
      );
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
        "Error searching on Navidrome"
      );
    }
  };

  handleTokenError = async (
    error: Error | string,
    callbackFunction: () => void
  ): Promise<void> => {
    const { refreshNavidromeToken, onInvalidateDataSource } = this.props;
    const { navidromeAuth: navidromeUser = undefined } = this.context;

    if (!navidromeUser?.instance_url) {
      onInvalidateDataSource(
        this as any,
        <span>
          Please{" "}
          <Link to="/settings/music-services/details/">
            re-connect your Navidrome account
          </Link>
        </span>
      );
      return;
    }

    try {
      this.accessToken = await refreshNavidromeToken();
      callbackFunction();
    } catch (refreshError) {
      onInvalidateDataSource(
        this as any,
        <span>
          Please{" "}
          <Link to="/settings/music-services/details/">
            re-connect your Navidrome account
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
      handleError(error.message, "Navidrome playback error");
    }
  };

  seekToPositionMs = (msTimecode: number): void => {
    const audioElement = this.audioRef.current;
    if (audioElement) {
      audioElement.currentTime = msTimecode / 1000;
    }
  };

  canSearchAndPlayTracks = (): boolean => {
    const { navidromeAuth: navidromeUser = undefined } = this.context;
    return NavidromePlayer.hasPermissions(navidromeUser);
  };

  datasourceRecordsListens = (): boolean => {
    return true; // record listens
  };

  setAudioSrc = (audioElement: HTMLAudioElement, src: string): void => {
    // eslint-disable-next-line no-param-reassign
    audioElement.src = src;
  };

  updateVolume = (): void => {
    const { volume = 100 } = this.props;
    const audioElement = this.audioRef.current;
    if (audioElement) {
      const safeVolume = Number.isFinite(volume) ? volume : 100;
      audioElement.volume = safeVolume / 100;
    }
  };

  pauseAudio = (): void => {
    const audioElement = this.audioRef.current;
    if (audioElement && !audioElement.paused) {
      audioElement.pause();
    }
  };

  render() {
    const { show } = this.props;
    const { currentTrack } = this.state;
    const artworkUrl = this.getTrackArtworkUrl(currentTrack);

    return (
      <div className={`navidrome-player ${show ? "" : "hidden"}`}>
        <audio ref={this.audioRef} crossOrigin="anonymous" preload="metadata">
          <track kind="captions" />
        </audio>
        {artworkUrl && (
          <div>
            <img alt="coverart" className="img-fluid" src={artworkUrl} />
          </div>
        )}
      </div>
    );
  }
}
