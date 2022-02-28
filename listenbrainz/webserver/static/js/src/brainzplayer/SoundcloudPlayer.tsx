import * as React from "react";
import { get as _get, throttle as _throttle } from "lodash";
import { DataSourceType, DataSourceProps } from "./BrainzPlayer";

require("../../lib/soundcloud-player-api");

enum SoundCloudHTML5WidgetEvents {
  LOAD_PROGRESS = "loadProgress", // fired periodically while the sound is loading.
  PLAY_PROGRESS = "playProgress", // fired periodically while the sound is playing.
  PLAY = "play", // fired when the sound begins to play.
  PAUSE = "pause", // fired when the sound pauses.
  FINISH = "finish", // fired when the sound finishes.
  SEEK = "seek", // fired when the user seeks.
  READY = "ready", // fired when the widget has loaded its data and is ready to accept external calls.
  OPEN_SHARE_PANEL = "sharePanelOpened", // Fired when the user clicks the download button.
  CLICK_DOWNLOAD = "downloadClicked", // Fired when the user clicks the buy button.
  CLICK_BUY = "buyClicked", // Fired when the share panel is opened. This happens when the user clicks the "Share" button, and at the end of the last sound.
  ERROR = "error", // Fired when an error message is displayed.
}

interface SoundCloudHTML5Widget {
  play(): void;
  pause(): void;
  toggle(): void;
  seekTo(milliseconds: number): void;
  currentTime(): number;
  bind(eventName: string, handler: Function): void;
  unbind(eventName: string): void;
  load(url: string, options: any): void;
  setVolume(volume: number): void;
  // Getters
  getVolume(callback: Function): void;
  getDuration(callback: Function): void;
  getPosition(callback: Function): void;
  getSounds(callback: Function): void;
  getCurrentSound(callback: Function): void;
  getCurrentSoundIndex(callback: Function): void;
  isPaused(callback: Function): void;
  // Navigation (if multiple sounds loaded)
  next(): void;
  prev(): void;
  skip(soundIndex: number): void;
}

type ProgressEvent = {
  soundId: number;
  loadedProgress: number;
  currentPosition: number;
  relativePosition: number;
};

type SoundcloudPlayerState = {
  currentSoundId?: number;
};

export default class SoundcloudPlayer
  extends React.Component<DataSourceProps, SoundcloudPlayerState>
  implements DataSourceType {
  static isListenFromThisService(listen: Listen | JSPFTrack): boolean {
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    return !!originURL && /soundcloud\.com/.test(originURL);
  }

  public name = "soundcloud";
  public domainName = "soundcloud.com";
  iFrameRef?: React.RefObject<HTMLIFrameElement>;
  soundcloudPlayer?: SoundCloudHTML5Widget;
  retries = 0;
  // HTML widget options: https://developers.soundcloud.com/docs/api/html5-widget#parameters
  options = {
    auto_play: true,
    show_artwork: true,
    visual: true,
    buying: false,
    liking: false,
    download: false,
    sharing: false,
    show_comments: false,
    show_playcount: false,
    show_user: false,
    hide_related: true,
  };

  constructor(props: DataSourceProps) {
    super(props);
    this.state = { currentSoundId: undefined };
    this.iFrameRef = React.createRef();
  }

  componentDidMount = () => {
    const { onInvalidateDataSource } = this.props;
    if (!(window as any).SC) {
      onInvalidateDataSource(this, "Soundcloud JS API did not load properly.");
      // Fallback to uncontrolled iframe player?
      return;
    }
    if (!this.iFrameRef || !this.iFrameRef.current) {
      onInvalidateDataSource(this, "SoundCloud IFrame not found in page.");
      return;
    }

    this.soundcloudPlayer = (window as any).SC.Widget(
      this.iFrameRef.current
    ) as SoundCloudHTML5Widget;
    this.soundcloudPlayer.bind(
      SoundCloudHTML5WidgetEvents.READY,
      this.onReady.bind(this)
    );
  };

  componentDidUpdate(prevProps: DataSourceProps) {
    const { show } = this.props;
    if (prevProps.show === true && show === false && this.soundcloudPlayer) {
      this.soundcloudPlayer.pause();
    }
  }

  componentWillUnmount() {
    if (!this.soundcloudPlayer) {
      return;
    }
    try {
      this.soundcloudPlayer.unbind(SoundCloudHTML5WidgetEvents.FINISH);
      this.soundcloudPlayer.unbind(SoundCloudHTML5WidgetEvents.PAUSE);
      this.soundcloudPlayer.unbind(SoundCloudHTML5WidgetEvents.PLAY);
      this.soundcloudPlayer.unbind(SoundCloudHTML5WidgetEvents.PLAY_PROGRESS);
      this.soundcloudPlayer.unbind(SoundCloudHTML5WidgetEvents.ERROR);
      this.soundcloudPlayer.unbind(SoundCloudHTML5WidgetEvents.READY);
      // eslint-disable-next-line no-empty
    } catch (error) {}
  }

  static getSoundcloudURLFromListen = (
    listen: Listen | JSPFTrack
  ): string | undefined => {
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (originURL && /soundcloud\.com/.test(originURL)) {
      return originURL;
    }
    return undefined;
  };

  onReady = (): void => {
    if (!this.soundcloudPlayer) {
      return;
    }
    const { onTrackEnd } = this.props;
    this.soundcloudPlayer.bind(SoundCloudHTML5WidgetEvents.FINISH, onTrackEnd);
    this.soundcloudPlayer.bind(SoundCloudHTML5WidgetEvents.PAUSE, this.onPause);
    this.soundcloudPlayer.bind(SoundCloudHTML5WidgetEvents.PLAY, this.onPlay);
    this.soundcloudPlayer.bind(
      SoundCloudHTML5WidgetEvents.PLAY_PROGRESS,
      _throttle(this.onProgressChange, 2000, { leading: true, trailing: true })
    );
    this.soundcloudPlayer.bind(SoundCloudHTML5WidgetEvents.ERROR, this.onError);
  };

  onProgressChange = (event: ProgressEvent): void => {
    const { onProgressChange } = this.props;
    onProgressChange(event.currentPosition);
  };

  onPause = (event: ProgressEvent): void => {
    const { onPlayerPausedChange } = this.props;
    onPlayerPausedChange(true);
  };

  onPlay = (event: ProgressEvent): void => {
    const { onPlayerPausedChange } = this.props;
    // Detect new track loaded
    const { currentSoundId } = this.state;
    if (event.soundId !== currentSoundId) {
      this.setState({ currentSoundId: event.soundId });
      this.updateTrackInfo(event);
    }

    onPlayerPausedChange(false);
  };

  canSearchAndPlayTracks = (): boolean => {
    return false;
  };

  datasourceRecordsListens = (): boolean => {
    return false;
  };

  playListen = (listen: Listen | JSPFTrack) => {
    const { show, onTrackNotFound } = this.props;
    if (!show) {
      return;
    }
    if (!SoundcloudPlayer.isListenFromThisService(listen)) {
      onTrackNotFound();
      return;
    }
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (this.soundcloudPlayer) {
      this.soundcloudPlayer.load(originURL, this.options);
    } else if (this.retries <= 3) {
      this.retries += 1;
      setTimeout(this.playListen.bind(this, listen), 500);
    } else {
      // Abort!
      const { onInvalidateDataSource } = this.props;
      onInvalidateDataSource(this, "Soundcloud player did not load properly.");
    }
  };

  updateTrackInfo = (event?: ProgressEvent) => {
    const {
      onTrackInfoChange,
      onDurationChange,
      onProgressChange,
    } = this.props;
    if (!this.soundcloudPlayer) {
      return;
    }
    this.soundcloudPlayer.getCurrentSound((currentTrack: any) => {
      if (!currentTrack) {
        return;
      }
      const artwork: MediaImage[] = currentTrack.artwork_url
        ? [{ src: currentTrack.artwork_url }]
        : [];
      onTrackInfoChange(
        currentTrack.title,
        currentTrack.permalink_url,
        currentTrack.user?.username,
        undefined,
        artwork
      );
      onDurationChange(currentTrack.full_duration);
      if (event) {
        onProgressChange(event.currentPosition);
      }
    });
  };

  togglePlay = (): void => {
    if (!this.soundcloudPlayer) {
      return;
    }
    this.soundcloudPlayer.toggle();
  };

  seekToPositionMs = (msTimecode: number) => {
    if (!this.soundcloudPlayer) {
      return;
    }
    this.soundcloudPlayer.seekTo(msTimecode);
  };

  onError = (error: any): void => {
    const { handleError, onTrackNotFound } = this.props;
    handleError(error, "SoundCloud player error");
    onTrackNotFound();
  };

  render() {
    const { show } = this.props;
    return (
      <div className={`soundcloud ${!show ? "hidden" : ""}`}>
        <iframe
          id="soundcloud-iframe"
          ref={this.iFrameRef}
          title="Soundcloud player"
          width="100%"
          height="420px"
          scrolling="no"
          frameBorder="no"
          allow="autoplay"
          src="https://w.soundcloud.com/player/?auto_play=false"
        />
      </div>
    );
  }
}
