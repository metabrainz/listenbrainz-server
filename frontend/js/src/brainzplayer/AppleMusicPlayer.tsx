/* eslint-disable no-underscore-dangle */
import * as React from "react";
import { debounce as _debounce, get as _get, isString } from "lodash";
import { faApple } from "@fortawesome/free-brands-svg-icons";
import { getArtistName, getTrackName, loadScriptAsync } from "../utils/utils";
import { DataSourceProps, DataSourceType } from "./BrainzPlayer";

export type AppleMusicPlayerProps = DataSourceProps & {
  appleMusicUser?: AppleMusicUser;
};

export type AppleMusicPlayerState = {
  currentAppleMusicTrack?: any;
  progressMs: number;
  durationMs: number;
};

export default class AppleMusicPlayer
  extends React.Component<AppleMusicPlayerProps, AppleMusicPlayerState>
  implements DataSourceType {
  static hasPermissions = (appleMusicUser?: AppleMusicUser) => {
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
  // Saving the access token outside of React state , we do not need it for any rendering purposes
  // and it simplifies some of the closure issues we've had with old tokens.
  private accessToken = "";

  private readonly _boundOnPlaybackStateChange: (event: any) => any;
  private readonly _boundOnPlaybackTimeChange: (event: any) => any;
  private readonly _boundOnPlaybackDurationChange: (event: any) => any;
  private readonly _boundOnNowPlayingItemChange: (event: any) => any;

  appleMusicPlayer?: AppleMusicPlayerType;
  debouncedOnTrackEnd: () => void;

  constructor(props: AppleMusicPlayerProps) {
    super(props);
    this.state = {
      durationMs: 0,
      progressMs: 0,
    };

    this.accessToken = props.appleMusicUser?.music_user_token || "";

    this.debouncedOnTrackEnd = _debounce(props.onTrackEnd, 700, {
      leading: true,
      trailing: false,
    });

    // Do an initial check of the AppleMusic token permissions (scopes) before loading the SDK library
    if (AppleMusicPlayer.hasPermissions(props.appleMusicUser)) {
      window.addEventListener("musickitloaded", this.connectAppleMusicPlayer);
      loadScriptAsync(
        document,
        "https://js-cdn.music.apple.com/musickit/v3/musickit.js",
        true
      );
    } else {
      this.handleAccountError();
    }

    this._boundOnPlaybackStateChange = this.onPlaybackStateChange.bind(this);
    this._boundOnPlaybackTimeChange = this.onPlaybackTimeChange.bind(this);
    this._boundOnPlaybackDurationChange = this.onPlaybackDurationChange.bind(
      this
    );
    this._boundOnNowPlayingItemChange = this.onNowPlayingItemChange.bind(this);
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
    const { handleError } = this.props;
    if (retryCount > 5) {
      handleError("Could not play AppleMusic track", "Playback error");
      return;
    }
    if (!this.appleMusicPlayer) {
      await this.connectAppleMusicPlayer();
      return;
    }
    try {
      await this.appleMusicPlayer.setQueue({
        song: appleMusicId,
        startPlaying: true,
      });
    } catch (error) {
      handleError(error.message, "Error playing on Apple Music");
    }
  };

  canSearchAndPlayTracks = (): boolean => {
    return true;
  };

  searchAndPlayTrack = async (listen: Listen | JSPFTrack): Promise<void> => {
    if (!this.appleMusicPlayer) {
      return;
    }
    const trackName = getTrackName(listen);
    const artistName = getArtistName(listen);
    const releaseName = _get(listen, "track_metadata.release_name");
    const searchTerm = `${trackName} ${artistName} ${releaseName}`;
    if (!searchTerm) {
      return;
    }
    const response = await this.appleMusicPlayer.api.music(
      `/v1/catalog/us/search`,
      { term: searchTerm, types: "songs" }
    );
    const apple_music_id = response?.data?.results?.songs?.data?.[0]?.id;
    // eslint-disable-next-line no-console
    console.log("Apple Music Id:", apple_music_id);
    if (apple_music_id) {
      await this.appleMusicPlayer.authorize();
      await this.playAppleMusicId(apple_music_id);
    }
  };

  datasourceRecordsListens = (): boolean => {
    return false;
  };

  playListen = (listen: Listen | JSPFTrack): void => {
    const { show } = this.props;
    if (!show) {
      return;
    }
    const apple_music_id = AppleMusicPlayer.getURLFromListen(listen as Listen);
    // eslint-disable-next-line no-console
    console.log("Apple Music Id:", apple_music_id);
    if (apple_music_id) {
      this.appleMusicPlayer.authorize();
      this.playAppleMusicId(apple_music_id);
      return;
    }
    this.searchAndPlayTrack(listen);
  };

  togglePlay = (): void => {
    if (
      this.appleMusicPlayer.playbackState === MusicKit.PlaybackStates.playing ||
      this.appleMusicPlayer.playbackState === MusicKit.PlaybackStates.loading
    ) {
      this.appleMusicPlayer.pause();
    } else {
      console.log("Apple Music Player:", this.appleMusicPlayer);
      console.log("#######################################");
      this.appleMusicPlayer.authorize();
      this.appleMusicPlayer.play();
    }
  };

  stopAndClear = (): void => {
    // eslint-disable-next-line react/no-unused-state
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
    this.appleMusicPlayer.seekToTime(timeCode);
  };

  disconnectAppleMusicPlayer = (): void => {
    if (!this.appleMusicPlayer) {
      return;
    }
    this.appleMusicPlayer.removeEventListener(
      "playbackStateDidChange",
      this._boundOnPlaybackStateChange
    );
    this.appleMusicPlayer.removeEventListener(
      "playbackTimeDidChange",
      this._boundOnPlaybackTimeChange
    );
    this.appleMusicPlayer.removeEventListener(
      "playbackDurationDidChange",
      this._boundOnPlaybackDurationChange
    );
    this.appleMusicPlayer.removeEventListener(
      "nowPlayingItemDidChange",
      this._boundOnNowPlayingItemChange
    );
    this.appleMusicPlayer = null;
  };

  connectAppleMusicPlayer = async (): Promise<void> => {
    this.disconnectAppleMusicPlayer();

    const musickit = window.MusicKit;
    if (!musickit) {
      setTimeout(this.connectAppleMusicPlayer.bind(this), 1000);
      return;
    }
    await musickit.configure({
      developerToken: "developer token here",
      app: {
        name: "ListenBrainz",
        build: "latest",
      },
    });
    this.appleMusicPlayer = musickit.getInstance();
    await this.appleMusicPlayer.authorize();
    this.appleMusicPlayer.addEventListener(
      "playbackStateDidChange",
      this._boundOnPlaybackStateChange
    );
    this.appleMusicPlayer.addEventListener(
      "playbackTimeDidChange",
      this._boundOnPlaybackTimeChange
    );
    this.appleMusicPlayer.addEventListener(
      "playbackDurationDidChange",
      this._boundOnPlaybackDurationChange
    );
    this.appleMusicPlayer.addEventListener(
      "nowPlayingItemDidChange",
      this._boundOnNowPlayingItemChange
    );
  };

  onPlaybackStateChange = ({ state: currentState }: any) => {
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

  onPlaybackTimeChange = ({ currentPlaybackTime }: any) => {
    const { onProgressChange } = this.props;
    const { progressMs } = this.state;
    const currentPlaybackTimeMs = currentPlaybackTime * 1000;
    if (progressMs !== currentPlaybackTimeMs) {
      this.setState({ progressMs: currentPlaybackTimeMs });
      onProgressChange(currentPlaybackTimeMs);
    }
  };

  onPlaybackDurationChange = ({ duration }: any) => {
    const { onDurationChange } = this.props;
    const { durationMs } = this.state;
    const currentDurationMs = duration * 1000;
    if (durationMs !== currentDurationMs) {
      this.setState({ durationMs: currentDurationMs });
      onDurationChange(currentDurationMs);
    }
  };

  onNowPlayingItemChange = ({ item }: any) => {
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
    // eslint-disable-next-line no-console
    console.log("Now Playing Item Change:", item);
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
