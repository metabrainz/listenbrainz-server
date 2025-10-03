import * as React from "react";
import { get as _get, isString, throttle as _throttle } from "lodash";
import { Link } from "react-router";
import { faMusic } from "@fortawesome/free-solid-svg-icons";
import faFunkwhale from "../icons/faFunkwhale";
import { DataSourceProps, DataSourceType } from "./BrainzPlayer";
import {
  getArtistName,
  getTrackName,
  searchForFunkwhaleTrack,
} from "../../utils/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
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
    const musicService = _get(
      listen,
      "track_metadata.additional_info.music_service"
    );
    return (
      (isString(musicService) &&
        musicService.toLowerCase().includes("funkwhale")) ||
      Boolean(FunkwhalePlayer.getURLFromListen(listen))
    );
  }

  static getURLFromListen = (
    listen: Listen | JSPFTrack
  ): string | undefined => {
    const funkwhaleListenUrl = _get(
      listen,
      "track_metadata.additional_info.funkwhale_listen_url"
    );
    if (funkwhaleListenUrl) {
      return funkwhaleListenUrl;
    }

    // Check for legacy funkwhale_id
    const funkwhaleId = _get(
      listen,
      "track_metadata.additional_info.funkwhale_id"
    );
    if (funkwhaleId) {
      return funkwhaleId;
    }

    // Check for origin_url if we can confirm it's from Funkwhale
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (originURL) {
      // Check music_service field to confirm this is from Funkwhale
      const musicService = _get(
        listen,
        "track_metadata.additional_info.music_service"
      );
      if (musicService && musicService.toLowerCase().includes("funkwhale")) {
        return originURL;
      }

      // Also accept URLs that contain "funkwhale" in the domain
      if (/funkwhale/.test(originURL)) {
        return originURL;
      }
    }

    return undefined;
  };

  public name = "funkwhale";
  public domainName = false;
  public icon = faFunkwhale; // Custom Funkwhale FontAwesome icon
  public iconColor = dataSourcesInfo.funkwhale.color;

  audioRef: React.RefObject<HTMLAudioElement>;
  updateProgressInterval?: NodeJS.Timeout;
  accessToken = "";
  currentBlobUrl?: string;
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
      this.accessToken = funkwhaleUser!.access_token!;
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
    if (this.currentBlobUrl) {
      URL.revokeObjectURL(this.currentBlobUrl);
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

    handleError(errorMessage, "Funkwhale playback error");
  };

  onCanPlay = (): void => {
    const { currentTrack } = this.state;
    if (currentTrack) {
      this.updateTrackInfo();
    }
  };

  getTrackArtworkUrl = (track?: FunkwhaleTrack): string | null => {
    if (!track?.album?.cover?.urls) return null;
    return (
      track.album.cover.urls.large_square_crop ||
      track.album.cover.urls.medium_square_crop ||
      track.album.cover.urls.small_square_crop ||
      track.album.cover.urls.original ||
      null
    );
  };

  getArtistNamesFromTrack = (track: FunkwhaleTrack): string => {
    if (!track.artist_credit || track.artist_credit.length === 0) {
      return "";
    }

    // Build artist name string using credits and joinphrases
    return track.artist_credit
      .map((credit, index) => {
        const name = credit.credit || credit.artist.name;
        const isLastItem = index === track.artist_credit!.length - 1;
        const joinphrase =
          !isLastItem && credit.joinphrase ? credit.joinphrase : "";
        return name + joinphrase;
      })
      .join("");
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
      currentTrack.fid || "",
      this.getArtistNamesFromTrack(currentTrack),
      currentTrack.album?.title || "",
      artwork
    );
  };

  playListen = async (listen: Listen | JSPFTrack): Promise<void> => {
    // For Funkwhale, we always search for tracks by name since
    // listens from history may contain federation URLs or library URLs
    // that don't work well for direct playback
    await this.searchAndPlayTrack(listen);
  };

  getFunkwhaleInstanceURL = (): string => {
    const { funkwhaleAuth: funkwhaleUser = undefined } = this.context;
    if (!funkwhaleUser?.instance_url) {
      throw new Error(
        "No Funkwhale instance URL available - user not connected"
      );
    }
    return funkwhaleUser.instance_url;
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

        if (track.is_playable !== false) {
          const audioElement = this.audioRef.current;
          if (audioElement) {
            const authenticatedAudioUrl = await this.getAuthenticatedAudioUrl(
              track.listen_url
            );
            if (authenticatedAudioUrl) {
              this.setAudioSrc(audioElement, authenticatedAudioUrl);
              await audioElement.play();
              return;
            }
          }
        }
      }

      handleWarning(
        `"${trackName}" by ${artistName} is not available on your Funkwhale server`,
        "Track not available on Funkwhale"
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
        this,
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
        this,
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
    return false; // record listens
  };

  getAuthenticatedAudioUrl = async (
    listenUrl: string
  ): Promise<string | null> => {
    if (!this.accessToken) return null;

    try {
      const fullUrl = listenUrl.startsWith("/")
        ? this.getFunkwhaleInstanceURL() + listenUrl
        : listenUrl;

      const response = await fetch(fullUrl, {
        headers: {
          Authorization: `Bearer ${this.accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const audioBlob = await response.blob();
      return URL.createObjectURL(audioBlob);
    } catch (error) {
      return null;
    }
  };

  setAudioSrc = (audioElement: HTMLAudioElement, src: string): void => {
    if (this.currentBlobUrl) {
      URL.revokeObjectURL(this.currentBlobUrl);
      this.currentBlobUrl = undefined;
    }
    // eslint-disable-next-line no-param-reassign
    audioElement.src = src;

    if (src.startsWith("blob:")) {
      this.currentBlobUrl = src;
    }
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
      <div
        className={`funkwhale-player ${show ? "" : "hidden"}`}
        data-testid="funkwhale-player"
      >
        <audio
          data-testid="funkwhale-audio"
          ref={this.audioRef}
          crossOrigin="anonymous"
          preload="metadata"
        >
          <track kind="captions" />
        </audio>
        {artworkUrl && (
          <div>
            <img
              alt="coverart"
              className="img-fluid"
              src={artworkUrl}
              crossOrigin="anonymous"
            />
          </div>
        )}
      </div>
    );
  }
}
