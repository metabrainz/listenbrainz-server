import * as React from "react";
import { get as _get } from "lodash";
import { DataSourceType, DataSourceProps } from "./BrainzPlayer";

require("../lib/soundcloud-player-api");

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
  currentListen?: Listen;
};

export default class SoundcloudPlayer
  extends React.Component<DataSourceProps, SoundcloudPlayerState>
  implements DataSourceType {
  soundcloudPlayer?: SoundCloudHTML5Widget;
  supportsSearch = false;
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

  componentDidMount = () => {
    if (!(window as any).SC) {
      const { onInvalidateDataSource } = this.props;
      onInvalidateDataSource(this, "Soundcloud JS API did not load properly.");
      // Fallback to uncontrolled iframe player?
      return;
    }
    const iframeElement = document.getElementById("soundcloud-iframe");
    this.soundcloudPlayer = (window as any).SC.Widget(
      iframeElement
    ) as SoundCloudHTML5Widget;
    this.soundcloudPlayer.bind(SoundCloudHTML5WidgetEvents.READY, this.onReady);
  };

  componentDidUpdate(prevProps: DataSourceProps) {
    const { show } = this.props;
    if (prevProps.show === true && show === false && this.soundcloudPlayer) {
      this.soundcloudPlayer.pause();
      // Clear currently playing sound
      // This will throw an error
      // this.soundcloudPlayer.load("fnord", this.options);
    }
  }

  componentWillUnmount() {
    if (!this.soundcloudPlayer) {
      return;
    }
    this.soundcloudPlayer.unbind(SoundCloudHTML5WidgetEvents.FINISH);
    this.soundcloudPlayer.unbind(SoundCloudHTML5WidgetEvents.PAUSE);
    this.soundcloudPlayer.unbind(SoundCloudHTML5WidgetEvents.PLAY);
    this.soundcloudPlayer.unbind(SoundCloudHTML5WidgetEvents.PLAY_PROGRESS);
    this.soundcloudPlayer.unbind(SoundCloudHTML5WidgetEvents.ERROR);
    this.soundcloudPlayer.unbind(SoundCloudHTML5WidgetEvents.READY);
  }

  onReady = (): void => {
    if (!this.soundcloudPlayer) {
      return;
    }
    const { onTrackEnd, onPlayerPausedChange, onProgressChange } = this.props;
    this.soundcloudPlayer.bind(SoundCloudHTML5WidgetEvents.FINISH, onTrackEnd);
    this.soundcloudPlayer.bind(
      SoundCloudHTML5WidgetEvents.PAUSE,
      onPlayerPausedChange.bind(true)
    );
    this.soundcloudPlayer.bind(SoundCloudHTML5WidgetEvents.PLAY, this.onPlay);
    this.soundcloudPlayer.bind(
      SoundCloudHTML5WidgetEvents.PLAY_PROGRESS,
      onProgressChange
    );
    this.soundcloudPlayer.bind(SoundCloudHTML5WidgetEvents.ERROR, this.onError);
  };

  onPlay = (event: ProgressEvent): void => {
    const {
      onPlayerPausedChange,
      onTrackNotFound,
      onTrackInfoChange,
      onDurationChange,
    } = this.props;
    // Detect new track loaded
    if (
      event.loadedProgress === 0 &&
      event.currentPosition === 0 &&
      event.relativePosition === 0
    ) {
      if (!this.soundcloudPlayer) {
        return;
      }
      this.soundcloudPlayer.getCurrentSound((currentTrack: any) => {
        if (!currentTrack) {
          onTrackNotFound();
        }
        onTrackInfoChange(currentTrack.title, currentTrack.user?.username);
        onDurationChange(currentTrack.full_duration);
      });
    }

    onPlayerPausedChange.bind(false);
  };

  playListen = (listen: Listen) => {
    const { show, onTrackNotFound } = this.props;
    if (!show) {
      return;
    }
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (/soundcloud\.com/.test(originURL)) {
      if (this.soundcloudPlayer) {
        const fullURL = `https://w.soundcloud.com/player/?url=${originURL}`;
        this.soundcloudPlayer.load(fullURL, this.options);
      } else if (this.retries <= 3) {
        this.retries += 1;
        setTimeout(this.playListen.bind(this, listen), 650);
      } else {
        // Abort!
        const { onInvalidateDataSource } = this.props;
        onInvalidateDataSource(
          this,
          "Soundcloud player did not load properly."
        );
      }
    } else {
      onTrackNotFound();
    }
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
          title="Soundcloud player"
          width="100%"
          height="166"
          scrolling="no"
          frameBorder="no"
          allow="autoplay"
          // src=""
          src="https://w.soundcloud.com/player/"
          // src={`https://w.soundcloud.com/player/?url=${encodeURIComponent(
          //   url
          // )}${optionsString}`}
        />
      </div>
    );
  }
}
