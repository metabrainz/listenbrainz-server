import * as React from "react";
import { get as _get, isString, throttle as _throttle } from "lodash";
import { faSoundcloud } from "@fortawesome/free-brands-svg-icons";
import { Link } from "react-router-dom";
import { DataSourceProps, DataSourceType } from "./BrainzPlayer";
import {
  getArtistName,
  getTrackName,
  searchForSoundcloudTrack,
} from "../../utils/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { BrainzPlayerContext } from "./BrainzPlayerContext";
import { dataSourcesInfo } from "../../settings/brainzplayer/BrainzPlayerSettings";

require("../../../lib/soundcloud-player-api");

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

export type SoundcloudPlayerState = {
  currentSound?: SoundCloudTrack;
};

export type SoundCloudPlayerProps = DataSourceProps & {
  refreshSoundcloudToken: () => Promise<string>;
};

export default class SoundcloudPlayer
  extends React.Component<SoundCloudPlayerProps, SoundcloudPlayerState>
  implements DataSourceType {
  static contextType = GlobalAppContext;
  static hasPermissions = (soundcloudUser?: SoundCloudUser) => {
    return Boolean(soundcloudUser?.access_token);
  };

  static isListenFromThisService(listen: Listen | JSPFTrack): boolean {
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    return !!originURL && /soundcloud\.com/.test(originURL);
  }

  static getURLFromListen = (
    listen: Listen | JSPFTrack
  ): string | undefined => {
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (originURL && /soundcloud\.com/.test(originURL)) {
      return originURL;
    }
    return undefined;
  };

  public name = "soundcloud";
  public domainName = "soundcloud.com";
  public icon = faSoundcloud;
  public iconColor = dataSourcesInfo.soundcloud.color;
  iFrameRef?: React.RefObject<HTMLIFrameElement>;
  soundcloudPlayer?: SoundCloudHTML5Widget;
  retries = 0;
  // HTML widget options: https://developers.soundcloud.com/docs/api/html5-widget#parameters
  options = {
    auto_play: true,
    show_artwork: false,
    visual: false,
    buying: false,
    liking: false,
    download: false,
    sharing: false,
    show_comments: false,
    show_playcount: false,
    show_user: false,
    hide_related: true,
  };

  // Saving the access token outside of React state , we do not need it for any rendering purposes
  // and it simplifies some of the closure issues we've had with old tokens.
  private accessToken = "";
  private authenticationRetries = 0;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: SoundCloudPlayerProps) {
    super(props);
    this.state = { currentSound: undefined };
    this.iFrameRef = React.createRef();
  }

  componentDidMount() {
    const { soundcloudAuth: soundcloudUser = undefined } = this.context;
    this.accessToken = soundcloudUser?.access_token || "";
    // initial permissions check
    if (!SoundcloudPlayer.hasPermissions(soundcloudUser)) {
      this.handleAccountError();
    }

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
  }

  componentDidUpdate(prevProps: DataSourceProps) {
    const { show, volume } = this.props;
    if (prevProps.volume !== volume && this.soundcloudPlayer?.setVolume) {
      this.soundcloudPlayer?.setVolume((volume ?? 100) / 100);
    }

    if (prevProps.show && !show && this.soundcloudPlayer) {
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
    const { currentSound } = this.state;
    if (event.soundId !== currentSound?.id) {
      this.updateTrackInfo(event);
    }

    onPlayerPausedChange(false);
  };

  canSearchAndPlayTracks = (): boolean => {
    const { soundcloudAuth: soundcloudUser = undefined } = this.context;
    // check if the user is authed to search with the SoundCloud API
    return Boolean(soundcloudUser) && Boolean(soundcloudUser?.access_token);
  };

  datasourceRecordsListens = (): boolean => {
    return false;
  };

  searchAndPlayTrack = async (listen: Listen | JSPFTrack): Promise<void> => {
    const trackName = getTrackName(listen);
    const artistName = getArtistName(listen);
    const releaseName = trackName
      ? ""
      : _get(listen, "track_metadata.release_name");
    const { handleError, handleWarning, onTrackNotFound } = this.props;
    if (!trackName && !artistName && !releaseName) {
      handleWarning(
        "We are missing a track title, artist or album name to search on Soundcloud",
        "Not enough info to search on Soundcloud"
      );
      onTrackNotFound();
      return;
    }

    try {
      const streamUrl = await searchForSoundcloudTrack(
        this.accessToken,
        trackName,
        artistName,
        releaseName
      );
      if (streamUrl) {
        this.playStreamUrl(streamUrl);
        return;
      }
      onTrackNotFound();
    } catch (errorObject) {
      if (errorObject.code === 401) {
        // Handle token error and try again if fixed
        await this.handleTokenError(
          errorObject.message,
          this.searchAndPlayTrack.bind(this, listen)
        );
      }
      if (errorObject.code === 400) {
        onTrackNotFound();
      }
      handleError(
        errorObject.message ?? errorObject,
        "Error searching on Soundcloud"
      );
    }
  };

  handleTokenError = async (
    error: Error | string | Spotify.Error,
    callbackFunction: () => void
  ): Promise<void> => {
    const { refreshSoundcloudToken, onTrackNotFound, handleError } = this.props;
    const { soundcloudAuth: soundcloudUser = undefined } = this.context;
    if (this.authenticationRetries > 5) {
      handleError(
        isString(error) ? error : error?.message,
        "Soundcloud token error"
      );
      onTrackNotFound();
      return;
    }
    this.authenticationRetries += 1;
    try {
      this.accessToken = await refreshSoundcloudToken();
      this.authenticationRetries = 0;
      if (soundcloudUser) {
        soundcloudUser.access_token = this.accessToken;
      }
      callbackFunction();
    } catch (refreshError) {
      handleError(refreshError, "Error connecting to SoundCloud");
    }
  };

  handleAccountError = (): void => {
    const errorMessage = (
      <p>
        In order to play music with SoundCloud, you will need a SoundCloud
        account linked to your ListenBrainz account.
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

  playListen = (listen: Listen | JSPFTrack) => {
    const { show, onTrackNotFound } = this.props;
    if (!show) {
      return;
    }
    if (SoundcloudPlayer.isListenFromThisService(listen)) {
      const originURL = _get(
        listen,
        "track_metadata.additional_info.origin_url"
      );
      this.playStreamUrl(originURL);
    } else {
      this.searchAndPlayTrack(listen);
    }
  };

  playStreamUrl = (streamUrl: string) => {
    if (this.soundcloudPlayer) {
      this.soundcloudPlayer.load(streamUrl, this.options);
    } else if (this.retries <= 3) {
      this.retries += 1;
      setTimeout(this.playStreamUrl.bind(this, streamUrl), 500);
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
    this.soundcloudPlayer.getCurrentSound((currentTrack: SoundCloudTrack) => {
      if (!currentTrack) {
        return;
      }
      this.setState({ currentSound: currentTrack });
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
      onDurationChange(currentTrack.duration);
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

  getAlbumArt = (): JSX.Element | null => {
    const { currentSound } = this.state;
    if (!currentSound || !currentSound.artwork_url) {
      return null;
    }
    return (
      <img
        alt="coverart"
        className="img-responsive"
        src={currentSound.artwork_url}
      />
    );
  };

  render() {
    const { show } = this.props;

    return (
      <div
        className={`soundcloud ${!show ? "hidden" : ""}`}
        data-testid={`soundcloud ${!show ? "hidden" : ""}`}
      >
        <iframe
          id="soundcloud-iframe"
          ref={this.iFrameRef}
          title="Soundcloud player"
          width="100%"
          height="420px"
          style={{ display: "none" }}
          scrolling="no"
          frameBorder="no"
          allow="autoplay"
          src="https://w.soundcloud.com/player/?auto_play=false"
        />
        <div>{this.getAlbumArt()}</div>
      </div>
    );
  }
}
