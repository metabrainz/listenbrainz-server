import * as React from "react";
import { get as _get, isString } from "lodash";
import { Link } from "react-router";
import {
  DataSourceProps,
  DataSourceType,
  DataSourceTypes,
} from "./BrainzPlayer";
import { getArtistName, getTrackName } from "../../utils/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { dataSourcesInfo } from "../../settings/brainzplayer/BrainzPlayerSettings";
import { currentDataSourceNameAtom, store } from "./BrainzPlayerAtoms";
import faTidal from "../icons/faTidal";

const TIDAL_SEARCH_API = "https://openapi.tidal.com/v2/search";

// Minimal type declarations for @tidal-music/player SDK
interface TidalCredentials {
  token: string;
  clientId: string;
  requestedScopes: string[];
}

interface TidalCredentialsProvider {
  getCredentials: () => Promise<TidalCredentials>;
}

interface TidalPlayerSDK {
  load: (
    request: { productId: string; productType: string },
    preload?: boolean
  ) => Promise<void>;
  play: () => Promise<void>;
  pause: () => Promise<void>;
  reset: () => Promise<void>;
  seek: (positionMs: number) => void;
  setVolume: (volume: number) => void;
  events: {
    subscribe: (handler: (event: TidalPlayerEvent) => void) => () => void;
  };
}

interface TidalPlaybackPayload {
  state: "NOT_LOADED" | "PLAYING" | "PAUSED" | "STALLED";
  duration: number;
  position: number;
}

interface TidalErrorPayload {
  code?: string;
  message?: string;
}

interface TidalPlayerEvent {
  type:
    | "playback-state-change"
    | "media-product-transition"
    | "end-of-queue"
    | "error";
  payload?: TidalPlaybackPayload | TidalErrorPayload;
}

export type TidalPlayerState = {};

export type TidalPlayerProps = DataSourceProps & {
  refreshTidalToken: () => Promise<string>;
};

export default class TidalPlayer
  extends React.Component<TidalPlayerProps, TidalPlayerState>
  implements DataSourceType {
  static contextType = GlobalAppContext;

  static hasPermissions = (tidalUser?: TidalUser) => {
    return Boolean(tidalUser?.access_token);
  };

  static isListenFromThisService(listen: Listen | JSPFTrack): boolean {
    const musicService = _get(
      listen,
      "track_metadata.additional_info.music_service"
    );
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    const tidalId = _get(listen, "track_metadata.additional_info.tidal_id");
    return (
      Boolean(tidalId) ||
      (isString(musicService) &&
        musicService.toLowerCase().includes("tidal")) ||
      (isString(originURL) && /tidal\.com/.test(originURL))
    );
  }

  static getURLFromListen = (
    listen: Listen | JSPFTrack
  ): string | undefined => {
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (originURL && /tidal\.com/.test(originURL)) {
      return originURL;
    }
    return undefined;
  };

  declare context: React.ContextType<typeof GlobalAppContext>;

  public name = "tidal";
  public domainName = "tidal.com";
  public icon = faTidal;
  public iconColor = dataSourcesInfo.tidal.color;

  private player: TidalPlayerSDK | null = null;
  private unsubscribeEvents: (() => void) | null = null;
  private authenticationRetries = 0;
  private accessToken = "";

  constructor(props: TidalPlayerProps) {
    super(props);
    this.state = {};
  }

  async componentDidMount() {
    const { tidalAuth } = this.context;
    if (!TidalPlayer.hasPermissions(tidalAuth)) {
      this.handleAccountError();
      return;
    }
    this.accessToken = tidalAuth?.access_token ?? "";
    await this.initializePlayer();
  }

  componentDidUpdate(prevProps: DataSourceProps) {
    const { volume } = this.props;
    if (prevProps.volume !== volume) {
      this.player?.setVolume((volume ?? 100) / 100);
    }
  }

  componentWillUnmount() {
    if (this.unsubscribeEvents) {
      this.unsubscribeEvents();
    }
    this.player?.reset();
  }

  initializePlayer = async (): Promise<void> => {
    const { onInvalidateDataSource } = this.props;
    const { tidalAuth } = this.context;
    try {
      // Dynamic import to avoid bundling issues if SDK is not installed
      // eslint-disable-next-line import/no-extraneous-dependencies
      const { init } = await import("@tidal-music/player");
      const credentialsProvider: TidalCredentialsProvider = {
        getCredentials: async () => ({
          token: this.accessToken,
          clientId: tidalAuth?.client_id ?? "",
          requestedScopes: [],
        }),
      };
      this.player = (await init(credentialsProvider)) as TidalPlayerSDK;
      this.unsubscribeEvents = this.player.events.subscribe(
        this.handlePlayerEvent
      );
    } catch (error) {
      onInvalidateDataSource(
        this as DataSourceTypes,
        "Tidal player SDK failed to load."
      );
    }
  };

  handlePlayerEvent = (event: TidalPlayerEvent): void => {
    const {
      onTrackEnd,
      onPlayerPausedChange,
      onProgressChange,
      onDurationChange,
      handleError,
      onTrackNotFound,
    } = this.props;

    switch (event.type) {
      case "playback-state-change": {
        const payload = event.payload as TidalPlaybackPayload;
        if (payload.state === "PLAYING") {
          onPlayerPausedChange(false);
          if (payload.duration) {
            onDurationChange(payload.duration * 1000);
          }
          onProgressChange(payload.position * 1000);
        } else if (payload.state === "PAUSED" || payload.state === "STALLED") {
          onPlayerPausedChange(true);
        }
        break;
      }
      case "end-of-queue":
        onTrackEnd();
        break;
      case "error": {
        const err = event.payload as TidalErrorPayload;
        handleError(
          err?.message ?? "Tidal playback error",
          "Tidal Player Error"
        );
        onTrackNotFound();
        break;
      }
      default:
        break;
    }
  };

  playListen = (listen: Listen | JSPFTrack): void => {
    const tidalId = _get(listen, "track_metadata.additional_info.tidal_id");
    if (tidalId) {
      this.playByTidalId(String(tidalId));
    } else {
      this.searchAndPlayTrack(listen);
    }
  };

  playByTidalId = async (trackId: string): Promise<void> => {
    const { onInvalidateDataSource } = this.props;
    if (!this.player) {
      await this.initializePlayer();
    }
    if (!this.player) {
      onInvalidateDataSource(
        this as DataSourceTypes,
        "Tidal player not initialized."
      );
      return;
    }
    try {
      await this.player.load(
        { productId: trackId, productType: "track" },
        false
      );
      await this.player.play();
    } catch (error) {
      await this.handleTokenError(
        error,
        this.playByTidalId.bind(this, trackId)
      );
    }
  };

  searchAndPlayTrack = async (listen: Listen | JSPFTrack): Promise<void> => {
    const { handleWarning, onTrackNotFound, handleError } = this.props;
    const trackName = getTrackName(listen);
    const artistName = getArtistName(listen);

    if (!trackName && !artistName) {
      handleWarning(
        "We are missing a track title and artist name to search on Tidal",
        "Not enough info to search on Tidal"
      );
      onTrackNotFound();
      return;
    }

    try {
      const query = [artistName, trackName].filter(Boolean).join(" ");
      const response = await fetch(
        `${TIDAL_SEARCH_API}?q=${encodeURIComponent(
          query
        )}&type=TRACKS&countryCode=US&limit=1`,
        {
          headers: {
            Authorization: `Bearer ${this.accessToken}`,
          },
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          await this.handleTokenError(
            new Error("Unauthorized"),
            this.searchAndPlayTrack.bind(this, listen)
          );
          return;
        }
        onTrackNotFound();
        return;
      }

      const data: TidalSearchResult = await response.json();
      const trackId = data?.data?.[0]?.resource?.id;
      if (trackId) {
        await this.playByTidalId(String(trackId));
      } else {
        onTrackNotFound();
      }
    } catch (error) {
      handleError(error.message ?? error, "Error searching on Tidal");
      onTrackNotFound();
    }
  };

  handleTokenError = async (
    error: any,
    retryCallback: () => void
  ): Promise<void> => {
    const { refreshTidalToken, handleError, onTrackNotFound } = this.props;
    if (this.authenticationRetries > 3) {
      handleError(error?.message ?? error, "Tidal token error");
      onTrackNotFound();
      return;
    }
    this.authenticationRetries += 1;
    try {
      this.accessToken = await refreshTidalToken();
      this.authenticationRetries = 0;
      retryCallback();
    } catch (refreshError) {
      handleError(refreshError, "Error refreshing Tidal token");
      onTrackNotFound();
    }
  };

  handleAccountError = (): void => {
    const errorMessage = (
      <p>
        In order to play music with Tidal, you will need a Tidal Premium account
        linked to your ListenBrainz account.
        <br />
        Please{" "}
        <Link to="/settings/music-services/details/">
          connect your Tidal account
        </Link>{" "}
        and refresh this page.
      </p>
    );
    const { onInvalidateDataSource } = this.props;
    onInvalidateDataSource(this as DataSourceTypes, errorMessage);
  };

  togglePlay = async (): Promise<void> => {
    if (!this.player) {
      return;
    }
    const { playerPaused, handleError, onTrackNotFound } = this.props;
    try {
      if (playerPaused) {
        await this.player.play();
      } else {
        await this.player.pause();
      }
    } catch (error) {
      handleError(error.message, "Tidal playback error");
      onTrackNotFound();
    }
  };

  stop = (): void => {
    this.player?.pause();
  };

  seekToPositionMs = (msTimecode: number): void => {
    this.player?.seek(msTimecode);
  };

  canSearchAndPlayTracks = (): boolean => {
    const { tidalAuth } = this.context;
    return TidalPlayer.hasPermissions(tidalAuth);
  };

  datasourceRecordsListens = (): boolean => {
    return false;
  };

  render() {
    const isCurrentDataSource =
      store.get(currentDataSourceNameAtom) === this.name;
    return (
      <div
        className={`tidal-player ${!isCurrentDataSource ? "hidden" : ""}`}
        data-testid="tidal-player"
      />
    );
  }
}
