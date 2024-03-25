/* eslint-disable no-underscore-dangle */
import * as React from "react";
import { get as _get, isString } from "lodash";
import { faApple } from "@fortawesome/free-brands-svg-icons";
import { getArtistName, getTrackName, loadScriptAsync } from "../utils/utils";
import { DataSourceProps, DataSourceType } from "./BrainzPlayer";

export type AppleMusicPlayerProps = DataSourceProps & {
  appleMusicUser?: AppleMusicUser;
  // eslint-disable-next-line react/no-unused-prop-types
  listenBrainzToken: string;
};

export type AppleMusicPlayerState = {
  currentAppleMusicTrack?: MusicKit.MediaItem;
  progressMs: number;
  durationMs: number;
};

export default class AppleMusicPlayer
  extends React.Component<AppleMusicPlayerProps, AppleMusicPlayerState>
  implements DataSourceType {
  static hasPermissions = (appleMusicUser?: AppleMusicUser) => {
    return Boolean(appleMusicUser?.developer_token);
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
  // Saving the developer token outside of React state , we do not need it for any rendering purposes
  // and it simplifies some of the closure issues we've had with old tokens.
  private readonly developerToken: string = "";
  private readonly musicUserToken: string = "";

  private readonly _boundOnPlaybackStateChange: (
    event: MusicKit.PlayerPlaybackState
  ) => void;

  private readonly _boundOnPlaybackTimeChange: (
    event: MusicKit.PlayerPlaybackTime
  ) => void;

  private readonly _boundOnPlaybackDurationChange: (
    event: MusicKit.PlayerDurationTime
  ) => void;

  private readonly _boundOnNowPlayingItemChange: (
    event: MusicKit.NowPlayingItem
  ) => void;

  appleMusicPlayer?: AppleMusicPlayerType;

  constructor(props: AppleMusicPlayerProps) {
    super(props);
    this.state = {
      durationMs: 0,
      progressMs: 0,
    };

    this.developerToken = props.appleMusicUser?.developer_token || "";
    this.musicUserToken = props.appleMusicUser?.music_user_token || "";

    // Do an initial check of whether the user wants to link Apple Music before loading the SDK library
    if (AppleMusicPlayer.hasPermissions(props.appleMusicUser)) {
      window.addEventListener("musickitloaded", this.connectAppleMusicPlayer);
      loadScriptAsync(
        document,
        "https://js-cdn.music.apple.com/musickit/v3/musickit.js"
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
    if (!this.appleMusicPlayer || !this.appleMusicPlayer.isAuthorized) {
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
      `/v1/catalog/{{storefrontId}}/search`,
      { term: searchTerm, types: "songs" }
    );
    const apple_music_id = response?.data?.results?.songs?.data?.[0]?.id;
    if (apple_music_id) {
      await this.playAppleMusicId(apple_music_id);
    }
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
    this.appleMusicPlayer?.seekToTime(timeCode);
  };

  disconnectAppleMusicPlayer = (): void => {
    if (!this.appleMusicPlayer) {
      return;
    }
    this.appleMusicPlayer?.removeEventListener(
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
    this.appleMusicPlayer = undefined;
  };

  connectAppleMusicPlayer = async (): Promise<void> => {
    this.disconnectAppleMusicPlayer();

    const musickit = window.MusicKit;
    if (!musickit) {
      setTimeout(this.connectAppleMusicPlayer.bind(this), 1000);
      return;
    }
    await musickit.configure({
      developerToken: this.developerToken,
      debug: true,
      app: {
        name: "ListenBrainz",
        build: "latest",
      },
    });
    this.appleMusicPlayer = musickit.getInstance();

    if (this.appleMusicPlayer && this.musicUserToken) {
      this.appleMusicPlayer.musicUserToken = this.musicUserToken;
    }

    this.appleMusicPlayer?.addEventListener(
      "playbackStateDidChange",
      this._boundOnPlaybackStateChange
    );
    this.appleMusicPlayer?.addEventListener(
      "playbackTimeDidChange",
      this._boundOnPlaybackTimeChange
    );
    this.appleMusicPlayer?.addEventListener(
      "playbackDurationDidChange",
      this._boundOnPlaybackDurationChange
    );
    this.appleMusicPlayer?.addEventListener(
      "nowPlayingItemDidChange",
      this._boundOnNowPlayingItemChange
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
