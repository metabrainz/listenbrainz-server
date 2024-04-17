import * as React from "react";
import { get as _get, isString } from "lodash";
import { faApple } from "@fortawesome/free-brands-svg-icons";
import {
  getArtistName,
  getTrackName,
  loadScriptAsync,
} from "../../utils/utils";
import { DataSourceProps, DataSourceType } from "./BrainzPlayer";

export type AppleMusicPlayerProps = DataSourceProps & {
  appleMusicUser?: AppleMusicUser;
};

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
  });
  return MusicKit.getInstance();
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

  appleMusicPlayer?: AppleMusicPlayerType;

  constructor(props: AppleMusicPlayerProps) {
    super(props);
    this.state = {
      durationMs: 0,
      progressMs: 0,
    };

    // Do an initial check of whether the user wants to link Apple Music before loading the SDK library
    if (AppleMusicPlayer.hasPermissions(props.appleMusicUser)) {
      loadAppleMusicKit().then(() => {
        this.connectAppleMusicPlayer();
      });
    } else {
      this.handleAccountError();
    }
  }

  componentDidUpdate(prevProps: DataSourceProps) {
    const { show } = this.props;
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
    const { appleMusicUser } = this.props;
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
    const releaseName = _get(listen, "track_metadata.release_name");
    const searchTerm = `${trackName} ${artistName} ${releaseName}`;
    if (!searchTerm) {
      onTrackNotFound();
      return;
    }
    try {
      const response = await this.appleMusicPlayer.api.music(
        `/v1/catalog/{{storefrontId}}/search`,
        { term: searchTerm, types: "songs" }
      );
      const apple_music_id = response?.data?.results?.songs?.data?.[0]?.id;
      if (apple_music_id) {
        await this.playAppleMusicId(apple_music_id);
        return;
      }
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
    const timeCode = Math.floor(msTimecode / 1000);
    this.appleMusicPlayer?.seekToTime(timeCode);
  };

  disconnectAppleMusicPlayer = (): void => {
    if (!this.appleMusicPlayer) {
      return;
    }
    this.appleMusicPlayer?.removeEventListener(
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
    const { appleMusicUser } = this.props;
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
      // this.appleMusicPlayer.musicUserToken = userToken;
    } catch (error) {
      console.debug(error);
      this.handleAccountError();
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
