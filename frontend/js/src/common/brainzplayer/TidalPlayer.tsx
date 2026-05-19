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

  private playerModule: typeof import("@tidal-music/player") | null = null;
  private eventListeners: Array<{
    name: string;
    fn: EventListenerOrEventListenerObject;
  }> = [];

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
    if (prevProps.volume !== volume && this.playerModule) {
      this.playerModule.setVolumeLevel(volume ?? 100);
    }
  }

  componentWillUnmount() {
    if (this.playerModule) {
      this.eventListeners.forEach(({ name, fn }) => {
        this.playerModule!.events.removeEventListener(name, fn);
      });
      this.playerModule.reset();
    }
  }

  initializePlayer = async (): Promise<void> => {
    const { onInvalidateDataSource } = this.props;
    const { tidalAuth } = this.context;
    try {
      // eslint-disable-next-line import/no-extraneous-dependencies
      const player = await import("@tidal-music/player");
      this.playerModule = player;

      player.bootstrap({
        outputDevices: false,
        players: [{ itemTypes: ["track"], player: "browser" }],
      });

      player.setCredentialsProvider({
        getCredentials: async () => ({
          token: this.accessToken,
          clientId: tidalAuth?.client_id ?? "",
          requestedScopes: [
            "playback",
            "entitlements.read",
            "search.read",
            "user.read",
          ],
        }),
      });

      this.bindEvent("playback-state-change", this.onPlaybackStateChange);
      this.bindEvent("media-product-transition", this.onMediaProductTransition);
      this.bindEvent("ended", this.onEnded);
      this.bindEvent("error", this.onError);
    } catch (error) {
      onInvalidateDataSource(
        this as DataSourceTypes,
        "Tidal player SDK failed to load."
      );
    }
  };

  private bindEvent = (name: string, fn: (e: Event) => void) => {
    const bound = fn as EventListenerOrEventListenerObject;
    this.playerModule!.events.addEventListener(name, bound);
    this.eventListeners.push({ name, fn: bound });
  };

  onPlaybackStateChange = (event: Event): void => {
    const { onPlayerPausedChange } = this.props;
    const { state } = (event as CustomEvent).detail ?? {};
    if (state === "PLAYING") {
      onPlayerPausedChange(false);
    } else if (state === "NOT_PLAYING" || state === "STALLED") {
      onPlayerPausedChange(true);
    }
  };

  onMediaProductTransition = (event: Event): void => {
    const { onDurationChange, onProgressChange } = this.props;
    const { playbackContext } = (event as CustomEvent).detail ?? {};
    if (playbackContext?.actualDuration) {
      onDurationChange(playbackContext.actualDuration * 1000);
    }
    onProgressChange(0);
  };

  onEnded = (event: Event): void => {
    const { onTrackEnd, onTrackNotFound } = this.props;
    const { reason } = (event as CustomEvent).detail ?? {};
    if (reason === "completed") {
      onTrackEnd();
    } else if (reason === "error") {
      onTrackNotFound();
    }
  };

  onError = (event: Event): void => {
    const { handleError, onTrackNotFound } = this.props;
    const err = (event as CustomEvent).detail ?? event;
    handleError(
      err?.message ?? String(err) ?? "Tidal playback error",
      "Tidal Player Error"
    );
    onTrackNotFound();
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
    if (!this.playerModule) {
      await this.initializePlayer();
    }
    if (!this.playerModule) {
      onInvalidateDataSource(
        this as DataSourceTypes,
        "Tidal player not initialized."
      );
      return;
    }
    try {
      await this.playerModule.load(
        {
          productId: trackId,
          productType: "track",
          sourceId: "listenbrainz",
          sourceType: "listenbrainz",
        },
        0,
        false
      );
      await this.playerModule.play();
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
    if (!this.playerModule) {
      return;
    }
    const { playerPaused, handleError, onTrackNotFound } = this.props;
    try {
      if (playerPaused) {
        await this.playerModule.play();
      } else {
        this.playerModule.pause();
      }
    } catch (error) {
      handleError(error.message, "Tidal playback error");
      onTrackNotFound();
    }
  };

  stop = (): void => {
    this.playerModule?.pause();
  };

  seekToPositionMs = (msTimecode: number): void => {
    // SDK seek takes seconds
    this.playerModule?.seek(msTimecode / 1000);
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
