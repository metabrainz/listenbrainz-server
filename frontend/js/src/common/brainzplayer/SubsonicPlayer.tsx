import * as React from "react";
import { throttle as _throttle } from "lodash";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { Link } from "react-router";
import {
  DataSourceProps,
  DataSourceType,
  DataSourceTypes,
} from "./BrainzPlayer";
import {
  getArtistName,
  getTrackName,
  searchForSubsonicTrack,
} from "../../utils/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { currentDataSourceNameAtom, store } from "./BrainzPlayerAtoms";

export type SubsonicPlayerState = {
  currentTrack?: NavidromeTrack;
};

export type SubsonicPlayerProps = DataSourceProps;

export type SubsonicPlayerConfig = {
  name: string;
  displayName: string;
  icon: IconProp;
  iconColor: string;
  className: string;
  testId: string;
  useProxy: boolean;
  proxyBaseUrl?: string;
};

export default abstract class SubsonicPlayer
  extends React.Component<SubsonicPlayerProps, SubsonicPlayerState>
  implements DataSourceType {
  static contextType = GlobalAppContext;

  public name!: string;
  public domainName = false;
  public icon!: IconProp;
  public iconColor!: string;

  audioRef: React.RefObject<HTMLAudioElement>;
  declare context: React.ContextType<typeof GlobalAppContext>;

  debouncedOnTrackEnd: () => void;
  abortController: AbortController | null = null;

  protected config: SubsonicPlayerConfig;

  protected constructor(
    props: SubsonicPlayerProps,
    config: SubsonicPlayerConfig
  ) {
    super(props);
    this.config = config;
    this.name = config.name;
    this.icon = config.icon;
    this.iconColor = config.iconColor;
    this.state = {
      currentTrack: undefined,
    };
    this.audioRef = React.createRef();

    this.debouncedOnTrackEnd = _throttle(this.handleTrackEnd, 700, {
      leading: true,
      trailing: false,
    });
  }

  async componentDidMount(): Promise<void> {
    if (this.hasPermissions()) {
      this.setupAudioListeners();
    }
    this.updateVolume();
  }

  componentDidUpdate(prevProps: DataSourceProps) {
    const { volume } = this.props;
    if (prevProps.volume !== volume) {
      this.updateVolume();
    }
  }

  componentWillUnmount(): void {
    this.cleanupAudioListeners();
    if (this.abortController) {
      this.abortController.abort();
    }
  }

  abstract getSubsonicUser(): NavidromeUser | undefined;
  // eslint-disable-next-line react/sort-comp
  abstract hasPermissions(): boolean;

  pause = () => {
    if (!this.audioRef?.current?.paused) {
      this.audioRef?.current?.pause();
    }
  };

  stop = () => {
    this.pause();
  };

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

  onLoadedMetadata = (event: Event): void => {
    const { onDurationChange } = this.props;
    const { currentTrack } = this.state;
    const audioElement = event.target as HTMLAudioElement;
    if (currentTrack?.duration) {
      onDurationChange(currentTrack.duration * 1000);
    } else {
      // fallback: Use browser duration but round it to avoid floating point errors
      onDurationChange(Math.round(audioElement.duration * 1000));
    }
  };

  onTimeUpdate = (event: Event): void => {
    const { onProgressChange } = this.props;
    const audioElement = event.target as HTMLAudioElement;
    onProgressChange(audioElement.currentTime * 1000);
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

  handleTrackEnd = (): void => {
    const { onTrackEnd } = this.props;
    onTrackEnd();
  };

  onError = (event: Event): void => {
    const { handleError, onTrackNotFound } = this.props;
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

    handleError(errorMessage, `${this.config.displayName} playback error`);
    onTrackNotFound();
  };

  onCanPlay = (): void => {
    const { currentTrack } = this.state;
    if (currentTrack) {
      this.updateTrackInfo();
    }
  };

  shouldUseProxy = (): boolean => {
    return this.config.useProxy;
  };

  isProxyingEnabled = (): boolean => {
    return this.shouldUseProxy();
  };

  setProxyingEnabled = (useProxy: boolean): void => {
    this.config.useProxy = useProxy;
  };

  getProxyUrl = (method: "search" | "stream" | "cover-art"): string => {
    return `${this.config.proxyBaseUrl?.replace(/\/$/, "")}/${method}/`;
  };

  getSubsonicInstanceURL = (): string => {
    const subsonicUser = this.getSubsonicUser();
    if (!subsonicUser?.instance_url) {
      throw new Error(
        `No ${this.config.displayName} instance URL available - user not connected`
      );
    }

    let instanceURL = subsonicUser.instance_url;
    if (instanceURL.endsWith("/")) {
      instanceURL = instanceURL.slice(0, -1);
    }

    return instanceURL;
  };

  getAuthParams = (): NavidromeAuthParams | null => {
    const subsonicUser = this.getSubsonicUser();
    if (
      !subsonicUser?.username ||
      !subsonicUser?.md5_auth_token ||
      !subsonicUser?.salt
    ) {
      return null;
    }

    // https://www.subsonic.org/pages/api.jsp
    // frontend/js/src/utils/navidromeTypes.d.ts -> NavidromeAuthParams
    // https://www.navidrome.org/docs/api/
    return {
      u: subsonicUser.username,
      t: subsonicUser.md5_auth_token,
      s: subsonicUser.salt,
      v: "1.16.1",
      c: "listenbrainz",
      f: "json",
    };
  };

  getAuthParamsString = (): string => {
    const params = this.getAuthParams();
    if (!params) {
      return "";
    }
    return new URLSearchParams(params).toString();
  };

  getTrackArtworkUrl = (track?: NavidromeTrack): string | null => {
    const coverArtId = track?.coverArt || track?.albumId;
    if (!coverArtId) return null;

    if (this.shouldUseProxy()) {
      return `${this.getProxyUrl("cover-art")}?id=${encodeURIComponent(
        coverArtId
      )}`;
    }

    const instanceURL = this.getSubsonicInstanceURL();
    const authParams = this.getAuthParamsString();

    if (!authParams) return null;

    return `${instanceURL}/rest/getCoverArt?id=${encodeURIComponent(
      coverArtId
    )}&${authParams}`;
  };

  getTrackWebUrl = (_track: NavidromeTrack): string => {
    try {
      return this.getSubsonicInstanceURL();
    } catch (error) {
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

  playListen = async (
    listen: Listen | JSPFTrack,
    streamingUrl?: string
  ): Promise<void> => {
    if (this.abortController) {
      this.abortController.abort();
    }
    // Create new AbortController for this search to prevent race conditions
    this.abortController = new AbortController();
    const searchController = this.abortController;

    // For Navidrome, we always search for tracks by name since
    // listens don't contain direct track IDs or URLs
    await this.searchAndPlayTrack(
      listen,
      this.abortController.signal,
      searchController
    );
  };

  getSubsonicStreamUrl = (trackId: string): string => {
    if (this.shouldUseProxy()) {
      return `${this.getProxyUrl("stream")}?id=${encodeURIComponent(trackId)}`;
    }

    const instanceURL = this.getSubsonicInstanceURL();
    const authParams = this.getAuthParamsString();

    if (!authParams) return "";

    return `${instanceURL}/rest/stream?id=${encodeURIComponent(
      trackId
    )}&${authParams}`;
  };

  searchAndPlayTrack = async (
    listen: Listen | JSPFTrack,
    signal: AbortSignal,
    searchController: AbortController
  ): Promise<void> => {
    const trackName = getTrackName(listen);
    const artistName = getArtistName(listen);
    const { handleError, handleWarning, onTrackNotFound } = this.props;

    if (!trackName && !artistName) {
      handleWarning(
        `We are missing a track title and artist name to search on ${this.config.displayName}`,
        `Not enough info to search on ${this.config.displayName}`
      );
      onTrackNotFound();
      return;
    }

    try {
      const authParams = this.getAuthParamsString();

      if (!this.shouldUseProxy() && !authParams) {
        handleWarning(
          `${this.config.displayName} authentication not available. Please check your connection.`,
          "Authentication Error"
        );
        onTrackNotFound();
        return;
      }

      const track = await searchForSubsonicTrack(
        this.shouldUseProxy() ? "" : this.getSubsonicInstanceURL(),
        this.shouldUseProxy() ? "" : authParams,
        trackName,
        artistName,
        signal,
        this.shouldUseProxy() ? this.getProxyUrl("search") : undefined
      );

      if (searchController !== this.abortController) {
        return;
      }

      if (track) {
        this.setState({ currentTrack: track });
        const audioElement = this.audioRef.current;
        if (audioElement) {
          const streamUrl = this.getSubsonicStreamUrl(track.id);
          this.setAudioSrc(audioElement, streamUrl);
          await audioElement.play();
          return;
        }
      }

      if (signal.aborted) {
        return;
      }

      onTrackNotFound();
    } catch (errorObject) {
      if (errorObject.name === "AbortError") {
        return;
      }

      if (errorObject.status === 401) {
        this.handleAuthenticationError();
        return;
      }
      handleError(
        errorObject.message ?? errorObject,
        `Error searching on ${this.config.displayName}`
      );
      onTrackNotFound();
    }
  };

  handleAuthenticationError = (): void => {
    const { onInvalidateDataSource } = this.props;

    onInvalidateDataSource(
      (this as unknown) as DataSourceTypes,
      <span>
        Please{" "}
        <Link to="/settings/music-services/details/">
          re-connect your {this.config.displayName} account
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
      const { handleError, onTrackNotFound } = this.props;
      handleError(error.message, `${this.config.displayName} playback error`);
      onTrackNotFound();
    }
  };

  seekToPositionMs = (msTimecode: number): void => {
    const audioElement = this.audioRef.current;
    if (audioElement) {
      audioElement.currentTime = msTimecode / 1000;
    }
  };

  canSearchAndPlayTracks = (): boolean => {
    return this.hasPermissions();
  };

  datasourceRecordsListens = (): boolean => {
    return false;
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
    if (audioElement) {
      audioElement.pause();
    }
  };

  render() {
    const { currentTrack } = this.state;
    const artworkUrl = this.getTrackArtworkUrl(currentTrack);
    const isCurrentDataSource =
      store.get(currentDataSourceNameAtom) === this.name;

    return (
      <div
        className={`${this.config.className} ${
          !isCurrentDataSource ? "hidden" : ""
        }`}
        data-testid={this.config.testId}
      >
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
