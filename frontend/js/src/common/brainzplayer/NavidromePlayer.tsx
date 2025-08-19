import * as React from "react";
import { get as _get, isString, throttle as _throttle } from "lodash";
import { Link } from "react-router";
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

export type NavidromePlayerProps = DataSourceProps;

export default class NavidromePlayer
  extends React.Component<NavidromePlayerProps, NavidromePlayerState>
  implements DataSourceType {
  static contextType = GlobalAppContext;
  static hasPermissions = (navidromeUser?: NavidromeUser) => {
    return Boolean(
      navidromeUser?.md5_auth_token && navidromeUser?.instance_url
    );
  };

  static isListenFromThisService(listen: Listen | JSPFTrack): boolean {
    const musicService = _get(
      listen,
      "track_metadata.additional_info.music_service"
    );
    return (
      isString(musicService) && musicService.toLowerCase().includes("navidrome")
    );
  }

  public name = "navidrome";
  public domainName = "navidrome";
  public icon = faNavidrome;
  public iconColor = dataSourcesInfo.navidrome.color;

  audioRef: React.RefObject<HTMLAudioElement>;
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
    const authParams = this.getAuthParamsString();

    // If auth not available, return null
    if (!authParams) return null;

    return `${instanceURL}/rest/getCoverArt?id=${track.albumId}&${authParams}`;
  };

  getTrackWebUrl = (track: NavidromeTrack): string => {
    try {
      const instanceURL = this.getNavidromeInstanceURL();

      // Link to the album page where the song appears instead
      if (track.albumId) {
        return `${instanceURL}/#/album/${track.albumId}/show`;
      }

      // Fallback to song list if no album ID is available
      return `${instanceURL}/#/song`;
    } catch (error) {
      // Fallback to empty string if we can't construct the URL
      return "";
    }
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
      this.getTrackWebUrl(currentTrack),
      currentTrack.artist || "",
      currentTrack.album || "",
      artwork
    );
  };

  playListen = async (listen: Listen | JSPFTrack): Promise<void> => {
    // For Navidrome, we always search for tracks by name since
    // listens don't contain direct track IDs or URLs
    await this.searchAndPlayTrack(listen);
  };

  getNavidromeInstanceURL = (): string => {
    const { navidromeAuth: navidromeUser = undefined } = this.context;
    if (!navidromeUser?.instance_url) {
      throw new Error(
        "No Navidrome instance URL available - user not connected"
      );
    }
    return navidromeUser?.instance_url || "";
  };

  getAuthParams = (): NavidromeAuthParams | null => {
    const { navidromeAuth: navidromeUser } = this.context;
    if (
      !navidromeUser?.username ||
      !navidromeUser?.md5_auth_token ||
      !navidromeUser?.salt
    ) {
      return null; // Return null instead of throwing error
    }

    return {
      u: navidromeUser.username,
      t: navidromeUser.md5_auth_token, // This is the MD5 hash token
      s: navidromeUser.salt,
      v: "1.16.1",
      c: "listenbrainz",
      f: "json",
    };
  };

  getAuthParamsString = (): string => {
    const params = this.getAuthParams();
    if (!params) {
      return ""; // Return empty string if auth not available
    }
    return new URLSearchParams(params).toString();
  };

  getNavidromeStreamUrl = (trackId: string): string => {
    const instanceURL = this.getNavidromeInstanceURL();
    const authParams = this.getAuthParamsString();

    // If auth not available, return empty string
    if (!authParams) return "";

    return `${instanceURL}/rest/stream?id=${trackId}&${authParams}`;
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
      const authParams = this.getAuthParamsString();

      // Check if authentication is available
      if (!authParams) {
        handleWarning(
          "Navidrome authentication not available. Please check your connection.",
          "Authentication Error"
        );
        onTrackNotFound();
        return;
      }

      const track = await searchForNavidromeTrack(
        this.getNavidromeInstanceURL(),
        authParams,
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
        this.handleAuthenticationError();
        return;
      }
      handleError(
        errorObject.message ?? errorObject,
        "Error searching on Navidrome"
      );
    }
  };

  handleAuthenticationError = (): void => {
    const { onInvalidateDataSource } = this.props;

    onInvalidateDataSource(
      this as any,
      <span>
        Please{" "}
        <Link to="/settings/music-services/details/">
          re-connect your Navidrome account
        </Link>
      </span>
    );
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
