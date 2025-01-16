import * as React from "react";
import { get as _get, deburr, escapeRegExp, isString } from "lodash";
import { faApple } from "@fortawesome/free-brands-svg-icons";
import { Link } from "react-router-dom";
import fuzzysort from "fuzzysort";
import {
  getArtistName,
  getTrackName,
  loadScriptAsync,
} from "../../utils/utils";
import { DataSourceProps, DataSourceType } from "./BrainzPlayer";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { BrainzPlayerContext } from "./BrainzPlayerContext";
import { dataSourcesInfo } from "../../settings/brainzplayer/BrainzPlayerSettings";

export type AppleMusicPlayerProps = DataSourceProps;

export type AppleMusicPlayerState = {
  currentAppleMusicTrack?: MusicKit.MediaItem;
  progressMs: number;
  durationMs: number;
};
export async function loadAppleMusicKit(): Promise<void> {
  if (!window.MusicKit) {
    loadScriptAsync(
      document,
      "https://js-cdn.music.apple.com/musickit/v3/musickit.js"
    );
    return new Promise((resolve) => {
      window.addEventListener("musickitloaded", () => {
        resolve();
      });
    });
  }
  return Promise.resolve();
}
export async function setupAppleMusicKit(developerToken?: string) {
  const { MusicKit } = window;
  if (!MusicKit) {
    throw new Error("Could not load Apple's MusicKit library");
  }
  if (!developerToken) {
    throw new Error(
      "Cannot configure Apple MusikKit without a valid developer token"
    );
  }
  await MusicKit.configure({
    developerToken,
    app: {
      name: "ListenBrainz",
      // TODO:  passs the GIT_COMMIT_SHA env variable to the globalprops and add it here as submission_client_version
      build: "latest",
      icon: "https://listenbrainz.org/static/img/ListenBrainz_logo_no_text.png",
    },
    suppressErrorDialog: true,
  });
  const musicKitInstance = MusicKit.getInstance();
  musicKitInstance.restrictedEnabled = false;
  return musicKitInstance;
}
export async function authorizeWithAppleMusic(
  musicKit: MusicKit.MusicKitInstance,
  setToken = true
): Promise<string | null> {
  const musicUserToken = await musicKit.authorize();
  if (musicUserToken && setToken) {
    try {
      // push token to LB server
      const request = await fetch("/settings/music-services/apple/set-token/", {
        method: "POST",
        body: musicUserToken,
      });
      if (!request.ok) {
        const { error } = await request.json();
        throw error;
      }
    } catch (error) {
      console.debug("Could not set user's Apple Music token:", error);
    }
  }
  return musicUserToken ?? null;
}
export default class AppleMusicPlayer
  extends React.Component<AppleMusicPlayerProps, AppleMusicPlayerState>
  implements DataSourceType {
  static contextType = GlobalAppContext;
  static hasPermissions = (appleMusicUser?: AppleMusicUser) => {
    return Boolean(appleMusicUser?.music_user_token);
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
      (isString(listeningFrom) &&
        listeningFrom.toLowerCase() === "apple_music") ||
      (isString(musicService) &&
        musicService.toLowerCase() === "music.apple.com") ||
      Boolean(AppleMusicPlayer.getURLFromListen(listen))
    );
  };

  static getURLFromListen(listen: Listen | JSPFTrack): string | undefined {
    return _get(listen, "track_metadata.additional_info.apple_music_id");
  }

  public name = "Apple Music";
  public domainName = "music.apple.com";
  public icon = faApple;
  public iconColor = dataSourcesInfo.appleMusic.color;

  appleMusicPlayer?: AppleMusicPlayerType;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: AppleMusicPlayerProps) {
    super(props);
    this.state = {
      durationMs: 0,
      progressMs: 0,
    };
  }

  async componentDidMount(): Promise<void> {
    const { appleAuth: appleMusicUser = undefined } = this.context;

    // Do an initial check of whether the user wants to link Apple Music before loading the SDK library
    if (AppleMusicPlayer.hasPermissions(appleMusicUser)) {
      loadAppleMusicKit().then(async () => {
        this.connectAppleMusicPlayer();

        try {
          // @ts-ignore
          // eslint-disable-next-line no-underscore-dangle
          await this.appleMusicPlayer?._services.apiManager.store.storekit.me();
        } catch (error) {
          this.handleAccountError();
        }
      });
    } else {
      this.handleAccountError();
    }
  }

  componentDidUpdate(prevProps: DataSourceProps) {
    const { show, volume } = this.props;
    const player = this.appleMusicPlayer;
    if (prevProps.volume !== volume && player) {
      player.volume = (volume ?? 100) / 100;
    }
    if (prevProps.show && !show) {
      this.stopAndClear();
    }
  }

  componentWillUnmount(): void {
    this.disconnectAppleMusicPlayer();
  }

  playAppleMusicId = async (
    appleMusicId: string,
    retryCount = 0
  ): Promise<void> => {
    const { handleError, onTrackNotFound } = this.props;
    if (retryCount > 5) {
      handleError("Could not play AppleMusic track", "Playback error");
      return;
    }
    if (!this.appleMusicPlayer || !this.appleMusicPlayer?.isAuthorized) {
      await this.connectAppleMusicPlayer();
      await this.playAppleMusicId(appleMusicId, retryCount);
      return;
    }
    try {
      await this.appleMusicPlayer.setQueue({
        song: appleMusicId,
        startPlaying: true,
      });
    } catch (error) {
      handleError(error.message, "Error playing on Apple Music");
      onTrackNotFound();
    }
  };

  canSearchAndPlayTracks = (): boolean => {
    const { appleAuth: appleMusicUser = undefined } = this.context;
    return AppleMusicPlayer.hasPermissions(appleMusicUser);
  };

  searchAndPlayTrack = async (listen: Listen | JSPFTrack): Promise<void> => {
    if (!this.appleMusicPlayer) {
      await this.connectAppleMusicPlayer();
      await this.searchAndPlayTrack(listen);
      return;
    }
    const { onTrackNotFound } = this.props;
    const trackName = getTrackName(listen);
    const artistName = getArtistName(listen);
    // Album name can give worse results, re;oving it from search terms
    // const releaseName = _get(listen, "track_metadata.release_name");
    const searchTerm = `${trackName} ${artistName}`;
    if (!searchTerm) {
      onTrackNotFound();
      return;
    }
    try {
      const response = await this.appleMusicPlayer.api.music(
        `/v1/catalog/{{storefrontId}}/search`,
        { term: searchTerm, types: "songs" }
      );
      // Remove accents from both the search term and the API results
      const trackNameWithoutAccents = deburr(trackName);
      const candidateMatches = response?.data?.results?.songs?.data.map(
        (candidate) => ({
          ...candidate,
          attributes: {
            ...candidate.attributes,
            name: deburr(candidate.attributes.name),
          },
        })
      );
      // Check if the first API result is a match
      if (
        new RegExp(escapeRegExp(trackNameWithoutAccents), "igu").test(
          candidateMatches?.[0]?.attributes.name
        )
      ) {
        // First result matches track title, assume it's the correct result
        await this.playAppleMusicId(candidateMatches[0].id);
        return;
      }
      // Fallback to best fuzzy match based on track title
      const fruzzyMatches = fuzzysort.go(
        trackNameWithoutAccents,
        candidateMatches,
        {
          key: "attributes.name",
          limit: 1,
        }
      );
      if (fruzzyMatches[0]) {
        await this.playAppleMusicId(fruzzyMatches[0].obj.id);
        return;
      }
      // No good match, onTrackNotFound will be called in the code block below
    } catch (error) {
      console.debug("Apple Music API request failed:", error);
    }
    onTrackNotFound();
  };

  datasourceRecordsListens = (): boolean => {
    return false;
  };

  playListen = async (listen: Listen | JSPFTrack): Promise<void> => {
    const { show } = this.props;
    if (!show) {
      return;
    }
    const apple_music_id = AppleMusicPlayer.getURLFromListen(listen as Listen);
    if (apple_music_id) {
      await this.playAppleMusicId(apple_music_id);
      return;
    }
    await this.searchAndPlayTrack(listen);
  };

  togglePlay = (): void => {
    if (
      this.appleMusicPlayer?.playbackState ===
        MusicKit.PlaybackStates.playing ||
      this.appleMusicPlayer?.playbackState === MusicKit.PlaybackStates.loading
    ) {
      this.appleMusicPlayer?.pause();
    } else {
      this.appleMusicPlayer?.play();
    }
  };

  stopAndClear = (): void => {
    this.setState({ currentAppleMusicTrack: undefined });
    if (this.appleMusicPlayer) {
      this.appleMusicPlayer.pause();
    }
  };

  handleAccountError = (): void => {
    const errorMessage = (
      <p>
        In order to play music with AppleMusic, you will need a AppleMusic
        Premium account linked to your ListenBrainz account.
        <br />
        Please try to{" "}
        <Link to="/settings/music-services/details/">
          link for &quot;playing music&quot; feature
        </Link>{" "}
        and refresh this page
      </p>
    );
    const { onInvalidateDataSource } = this.props;
    onInvalidateDataSource(this, errorMessage);
  };

  seekToPositionMs = (msTimecode: number): void => {
    const timeCode = Math.floor(msTimecode / 1000);
    this.appleMusicPlayer?.seekToTime(timeCode);
  };

  disconnectAppleMusicPlayer = (): void => {
    if (!this.appleMusicPlayer) {
      return;
    }
    this.appleMusicPlayer.removeEventListener(
      "playbackStateDidChange",
      this.onPlaybackStateChange.bind(this)
    );
    this.appleMusicPlayer.removeEventListener(
      "playbackTimeDidChange",
      this.onPlaybackTimeChange.bind(this)
    );
    this.appleMusicPlayer.removeEventListener(
      "playbackDurationDidChange",
      this.onPlaybackDurationChange.bind(this)
    );
    this.appleMusicPlayer.removeEventListener(
      "nowPlayingItemDidChange",
      this.onNowPlayingItemChange.bind(this)
    );
    this.appleMusicPlayer = undefined;
  };

  connectAppleMusicPlayer = async (retryCount = 0): Promise<void> => {
    this.disconnectAppleMusicPlayer();
    const { appleAuth: appleMusicUser = undefined } = this.context;
    try {
      this.appleMusicPlayer = await setupAppleMusicKit(
        appleMusicUser?.developer_token
      );
    } catch (error) {
      console.debug(error);
      if (retryCount >= 5) {
        const { onInvalidateDataSource } = this.props;
        onInvalidateDataSource(
          this,
          "Could not load Apple's MusicKit library after 5 retries"
        );
        return;
      }
      setTimeout(this.connectAppleMusicPlayer.bind(this, retryCount + 1), 1000);
      return;
    }
    try {
      const userToken = await authorizeWithAppleMusic(this.appleMusicPlayer);
      if (userToken === null) {
        throw new Error("Could not retrieve Apple Music authorization token");
      }
      if (appleMusicUser) {
        appleMusicUser.music_user_token = userToken;
      }
    } catch (error) {
      console.debug(error);
      this.handleAccountError();
    }

    if (!this.appleMusicPlayer) {
      return;
    }

    this.appleMusicPlayer.addEventListener(
      "playbackStateDidChange",
      this.onPlaybackStateChange.bind(this)
    );
    this.appleMusicPlayer.addEventListener(
      "playbackTimeDidChange",
      this.onPlaybackTimeChange.bind(this)
    );
    this.appleMusicPlayer.addEventListener(
      "playbackDurationDidChange",
      this.onPlaybackDurationChange.bind(this)
    );
    this.appleMusicPlayer.addEventListener(
      "nowPlayingItemDidChange",
      this.onNowPlayingItemChange.bind(this)
    );
  };

  onPlaybackStateChange = ({
    state: currentState,
  }: MusicKit.PlayerPlaybackState) => {
    const { onPlayerPausedChange, onTrackEnd } = this.props;
    if (currentState === MusicKit.PlaybackStates.playing) {
      onPlayerPausedChange(false);
    }
    if (currentState === MusicKit.PlaybackStates.paused) {
      onPlayerPausedChange(true);
    }
    if (currentState === MusicKit.PlaybackStates.completed) {
      onTrackEnd();
    }
  };

  onPlaybackTimeChange = ({
    currentPlaybackTime,
  }: MusicKit.PlayerPlaybackTime) => {
    const { onProgressChange } = this.props;
    const { progressMs } = this.state;
    const currentPlaybackTimeMs = currentPlaybackTime * 1000;
    if (progressMs !== currentPlaybackTimeMs) {
      this.setState({ progressMs: currentPlaybackTimeMs });
      onProgressChange(currentPlaybackTimeMs);
    }
  };

  onPlaybackDurationChange = ({ duration }: MusicKit.PlayerDurationTime) => {
    const { onDurationChange } = this.props;
    const { durationMs } = this.state;
    const currentDurationMs = duration * 1000;
    if (durationMs !== currentDurationMs) {
      this.setState({ durationMs: currentDurationMs });
      onDurationChange(currentDurationMs);
    }
  };

  onNowPlayingItemChange = ({ item }: MusicKit.NowPlayingItem) => {
    if (!item) {
      return;
    }
    const { onTrackInfoChange } = this.props;
    const { name, artistName, albumName, url, artwork } = item.attributes;
    let mediaImages: Array<MediaImage> | undefined;
    if (artwork) {
      mediaImages = [
        {
          src: artwork.url
            .replace("{w}", artwork.width)
            .replace("{h}", artwork.height),
          sizes: `${artwork.width}x${artwork.height}`,
        },
      ];
    }
    onTrackInfoChange(name, url, artistName, albumName, mediaImages);
    this.setState({ currentAppleMusicTrack: item });
  };

  getAlbumArt = (): JSX.Element | null => {
    const { currentAppleMusicTrack } = this.state;
    if (
      !currentAppleMusicTrack ||
      !currentAppleMusicTrack.attributes ||
      !currentAppleMusicTrack.attributes.artwork
    ) {
      return null;
    }
    const { artwork } = currentAppleMusicTrack.attributes;
    return (
      <img
        alt="coverart"
        className="img-responsive"
        src={artwork.url
          .replace("{w}", artwork.width)
          .replace("{h}", artwork.height)}
      />
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
