import * as React from "react";

import YouTube, { Options } from "react-youtube";
import {
  get as _get,
  isEqual as _isEqual,
  isFunction as _isFunction,
  isNil as _isNil,
  isString as _isString,
  throttle,
} from "lodash";
import Draggable, { DraggableData, DraggableEvent } from "react-draggable";
import { ResizableBox, ResizeCallbackData } from "react-resizable";
import "react-resizable/css/styles.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowsAlt,
  faWindowMaximize,
  faWindowMinimize,
  faTimes,
  faExpand,
  faCompress,
} from "@fortawesome/free-solid-svg-icons";
import { faYoutube } from "@fortawesome/free-brands-svg-icons";
import { Link } from "react-router";
import {
  getArtistName,
  getTrackName,
  searchForYoutubeTrack,
} from "../../utils/utils";
import { DataSourceProps, DataSourceType } from "./BrainzPlayer";
import { dataSourcesInfo } from "../../settings/brainzplayer/BrainzPlayerSettings";
import { currentDataSourceNameAtom, store } from "./BrainzPlayerAtoms";

export type YoutubePlayerProps = DataSourceProps & {
  youtubeUser?: YoutubeUser;
  refreshYoutubeToken: () => Promise<string>;
};

type YoutubePlayerState = {
  hidePlayer?: boolean;
  isExpanded?: boolean;
  width: number;
  height: number;
  x: number;
  y: number;
  isInteracting: boolean;
};

const DEFAULT_WIDTH = 350;
const DEFAULT_HEIGHT = 200;
const SIDEBAR_WIDTH = 200;
const PLAYER_HEIGHT = 60;
const BUTTON_HEIGHT = 30;
const SIDEBAR_BREAKPOINT = 992;
const EXPANDED_WIDTH = 1280;
const EXPANDED_HEIGHT = 720;
const PADDING = 10;
const PADDING_TOP = 30;

// For some reason Youtube types do not document getVideoData,
// which we need to determine if there was no search results
type ExtendedYoutubePlayer = {
  getVideoData?: () => { video_id?: string; author: string; title: string };
} & YT.Player;

export default class YoutubePlayer
  extends React.Component<YoutubePlayerProps, YoutubePlayerState>
  implements DataSourceType {
  static getVideoIDFromListen(listen: Listen | JSPFTrack): string | undefined {
    // This may be either video ID or video link.
    // In theory we could check the length of this string: currently all IDs have the length of 11
    // characters. However, we shouldn't do so as this is not in YouTube's specification and thus,
    // although unlikely, might change in the future.
    const youtubeId = _get(listen, "track_metadata.additional_info.youtube_id");

    const videoIdOrUrl =
      youtubeId ?? _get(listen, "track_metadata.additional_info.origin_url");
    if (_isString(videoIdOrUrl) && videoIdOrUrl.length) {
      /** Credit for this regular expression goes to Soufiane Sakhi:
       * https://stackoverflow.com/a/61033353/4904467
       */
      const youtubeURLRegexp = /(?:https?:\/\/)?(?:www\.|m\.)?youtu(?:\.be\/|be.com\/\S*(?:watch|embed)(?:(?:(?=\/[^&\s?]+(?!\S))\/)|(?:\S*v=|v\/)))([^&\s?]+)/g;
      const match = youtubeURLRegexp.exec(videoIdOrUrl);
      return match?.[1] ?? youtubeId;
    }

    return undefined;
  }

  static isListenFromThisService(listen: Listen | JSPFTrack): boolean {
    const videoId = YoutubePlayer.getVideoIDFromListen(listen);
    return Boolean(videoId);
  }

  /**
   * Youtube thumbnail URLs can be composed with <video_id>/<resolution><image>.jpg
   * where resolution is one of [hq , md, sd] and image is either 'default' (= 0)
   * or a number between 0 -> 3 (there are 4 thumbnails)
   */
  static getThumbnailsFromVideoid(videoId?: string) {
    let images: MediaImage[] = [];
    if (videoId) {
      images = [
        {
          src: `http://img.youtube.com/vi/${videoId}/sddefault.jpg`,
          sizes: "640x480",
          type: "image/jpg",
        },
        {
          src: `http://img.youtube.com/vi/${videoId}/hqdefault.jpg`,
          sizes: "480x360",
          type: "image/jpg",
        },
        {
          src: `http://img.youtube.com/vi/${videoId}/mqdefault.jpg`,
          sizes: "320x180",
          type: "image/jpg",
        },
      ];
    }
    return images;
  }

  static getURLFromVideoID(videoID: string): string {
    if (videoID) {
      return `https://www.youtube.com/watch?v=${videoID}`;
    }
    return "";
  }

  static getURLFromListen(listen: Listen | JSPFTrack): string | undefined {
    const youtubeId = this.getVideoIDFromListen(listen);
    if (youtubeId) {
      return `https://www.youtube.com/watch?v=${youtubeId}`;
    }

    return undefined;
  }

  public name = "youtube";
  public domainName = "youtube.com";
  public icon = faYoutube;
  public iconColor = dataSourcesInfo.youtube.color;
  youtubePlayer?: ExtendedYoutubePlayer;
  checkVideoLoadedTimerId?: NodeJS.Timeout;
  handleWindowResizeThrottle: (() => void) & {
    cancel: () => void;
    flush: () => void;
  };

  constructor(props: YoutubePlayerProps) {
    super(props);
    this.state = {
      hidePlayer: false,
      isExpanded: false,
      width: DEFAULT_WIDTH,
      height: DEFAULT_HEIGHT,
      x: 0,
      y: 0,
      isInteracting: false,
    };
    this.handleWindowResizeThrottle = throttle(this.handleWindowResize, 100);
  }

  componentDidMount(): void {
    window.addEventListener("resize", this.handleWindowResizeThrottle);
  }

  componentDidUpdate(prevProps: DataSourceProps) {
    const { volume, playerPaused } = this.props;
    if (prevProps.volume !== volume && this.youtubePlayer?.setVolume) {
      this.youtubePlayer?.setVolume(volume ?? 100);
    }
    if (prevProps.playerPaused && !playerPaused) {
      // Show player if playing music
      this.setState({ hidePlayer: false });
    }
  }

  componentWillUnmount(): void {
    window.removeEventListener("resize", this.handleWindowResizeThrottle);
    this.handleWindowResizeThrottle.cancel();
  }

  stop = () => {
    this.youtubePlayer?.stopVideo();
    // Clear playlist
    this.youtubePlayer?.cueVideoById("");
  };

  onReady = (event: YT.PlayerEvent): void => {
    this.youtubePlayer = event.target;
  };

  updateVideoInfo = (): void => {
    let title = "";
    let images: MediaImage[] = [];
    const { onTrackInfoChange, onDurationChange } = this.props;
    const videoData =
      this.youtubePlayer?.getVideoData && this.youtubePlayer.getVideoData();
    let videoId: string = "";
    let videoUrl: string = "";
    if (videoData) {
      title = videoData.title;
      videoId = videoData.video_id as string;
      images = YoutubePlayer.getThumbnailsFromVideoid(videoId);
      videoUrl = YoutubePlayer.getURLFromVideoID(videoId);
    }
    onTrackInfoChange(title, videoUrl, undefined, undefined, images);
    const duration = this.youtubePlayer?.getDuration();
    if (duration) {
      onDurationChange(duration * 1000);
    }
  };

  handlePlayerStateChanged = (event: YT.OnStateChangeEvent) => {
    const { data: state, target: player } = event;
    const {
      onPlayerPausedChange,
      onDurationChange,
      onProgressChange,
      onTrackInfoChange,
    } = this.props;
    if (state === YouTube.PlayerState.ENDED) {
      const { onTrackEnd } = this.props;
      onTrackEnd();
      return;
    }
    // New track loaded
    if (state === YouTube.PlayerState.UNSTARTED) {
      const title = _get(player, "playerInfo.videoData.title", "");
      const videoId = _get(player, "playerInfo.videoData.video_id", "");
      // The player info is sometimes missing a title initially.
      // We fallback to getting it with getVideoData method once the information is loaded in the player
      if (!title || !videoId) {
        setTimeout(this.updateVideoInfo, 2000);
      } else {
        const images: MediaImage[] = YoutubePlayer.getThumbnailsFromVideoid(
          videoId
        );
        const videoUrl = YoutubePlayer.getURLFromVideoID(videoId);
        onTrackInfoChange(title, videoUrl, undefined, undefined, images);
      }
    }
    if (state === YouTube.PlayerState.PAUSED) {
      onPlayerPausedChange(true);
    }
    if (state === YouTube.PlayerState.PLAYING) {
      onPlayerPausedChange(false);
    }
    onProgressChange(player.getCurrentTime() * 1000);
    const duration = _isFunction(player.getDuration) && player.getDuration();
    if (duration) {
      onDurationChange(duration * 1000);
    }
  };

  handleAccountError = (): void => {
    const errorMessage = (
      <p>
        In order to play music with Youtube, you will need a Youtube / Google
        account linked to your ListenBrainz account.
        <br />
        Please try to{" "}
        <Link to="/settings/music-services/details/">
          link for &quot;playing music&quot; feature
        </Link>{" "}
        and refresh this page
      </p>
    );
    const { onTrackNotFound, handleWarning } = this.props;
    handleWarning(errorMessage, "Youtube account error");
    onTrackNotFound();
  };

  searchAndPlayTrack = async (listen: Listen | JSPFTrack) => {
    const trackName = getTrackName(listen);
    const artistName = getArtistName(listen);
    // Using the releaseName has paradoxically given worst search results,
    // so we're only using it when track name isn't provided (for example for an album search)
    const releaseName = trackName
      ? ""
      : _get(listen, "track_metadata.release_name");

    const {
      handleWarning,
      onTrackNotFound,
      youtubeUser,
      refreshYoutubeToken,
    } = this.props;

    if (!this.youtubePlayer) {
      onTrackNotFound();
      return;
    }
    // If the user is not authed for Youtube API, show a helpful error message with link to connect
    if (!youtubeUser) {
      this.handleAccountError();
      return;
    }
    if (!trackName && !artistName && !releaseName) {
      handleWarning(
        "We are missing a track title, artist or album name to search on Youtube",
        "Not enough info to search on Youtube"
      );
      onTrackNotFound();
      return;
    }

    try {
      const { api_key } = youtubeUser;
      const videoIds = await searchForYoutubeTrack(
        api_key,
        trackName,
        artistName,
        releaseName,
        refreshYoutubeToken,
        this.handleAccountError
      );
      if (videoIds?.length) {
        this.playTrackById(videoIds[0]);
      } else {
        onTrackNotFound();
      }
    } catch (error) {
      handleWarning(error?.message ?? error.toString(), "Youtube player error");
      onTrackNotFound();
    }
  };

  playTrackById = (videoId: string): void => {
    if (!videoId || !this.youtubePlayer) {
      return;
    }
    if (videoId.startsWith("http")) {
      this.youtubePlayer.loadVideoByUrl(videoId);
    } else {
      this.youtubePlayer.loadVideoById(videoId);
    }
  };

  canSearchAndPlayTracks = (): boolean => {
    const { youtubeUser } = this.props;
    // check if the user is authed to search with the Youtube API
    return Boolean(youtubeUser) && Boolean(youtubeUser?.api_key);
  };

  datasourceRecordsListens = (): boolean => {
    return false;
  };

  playListen = (listen: Listen | JSPFTrack) => {
    const youtubeId = YoutubePlayer.getVideoIDFromListen(listen);

    if (youtubeId) {
      this.playTrackById(youtubeId);
    } else {
      this.searchAndPlayTrack(listen);
    }
  };

  togglePlay = (): void => {
    if (!this.youtubePlayer) {
      return;
    }
    const { playerPaused, onPlayerPausedChange } = this.props;
    if (playerPaused) {
      this.youtubePlayer.playVideo();
      onPlayerPausedChange(false);
    } else {
      this.youtubePlayer.pauseVideo();
      onPlayerPausedChange(true);
    }
  };

  seekToPositionMs = (msTimecode: number) => {
    if (!this.youtubePlayer) {
      return;
    }
    this.youtubePlayer.seekTo(msTimecode / 1000, true);
    this.youtubePlayer.playVideo();
  };

  onError = (event: YT.OnErrorEvent): void => {
    const { data: errorNumber } = event;
    const { handleError, onTrackNotFound } = this.props;
    if (this.checkVideoLoadedTimerId) {
      clearTimeout(this.checkVideoLoadedTimerId);
    }
    let message = "Something went wrong";
    switch (errorNumber) {
      case 101:
      case 150:
        message =
          "The owner of the requested video does not allow it to be played in embedded players.";
        break;
      case 5:
        message = "The requested content cannot be played in an HTML5 player.";
        break;
      case 2:
        message = "The request contained an invalid parameter value.";
        break;
      case 100:
        message = "The video requested was not found.";
        break;
      default:
        break;
    }
    handleError(message, "Youtube player error");
    onTrackNotFound();
  };

  // Handle hide button click
  handleHide = () => {
    const { playerPaused } = this.props;
    this.setState({ hidePlayer: true }, () => {
      if (!playerPaused) {
        this.togglePlay();
      }
    });
  };

  getMaxAvailableWidth = (): number => {
    let maxWidth = window.innerWidth - PADDING * 2;

    if (window.innerWidth > SIDEBAR_BREAKPOINT) {
      maxWidth -= SIDEBAR_WIDTH;
    }
    return maxWidth;
  };

  calculateDimensions = () => {
    const maxWidth = this.getMaxAvailableWidth();
    const targetWidth = Math.min(EXPANDED_WIDTH, maxWidth);
    const calculatedHeight = (targetWidth * 9) / 16 + BUTTON_HEIGHT;
    const maxHeight =
      window.innerHeight - (PLAYER_HEIGHT + BUTTON_HEIGHT + PADDING_TOP);
    const targetHeight = Math.min(
      EXPANDED_HEIGHT + BUTTON_HEIGHT,
      calculatedHeight,
      maxHeight
    );
    return {
      width: targetWidth,
      height: targetHeight,
    };
  };

  handleExpandToggle = () => {
    this.setState((prev) => {
      const isNowExpanded = !prev.isExpanded;

      if (isNowExpanded) {
        const { width, height } = this.calculateDimensions();
        return {
          isExpanded: true,
          width,
          height,
          x: 0,
          y: 0,
        };
      }
      return {
        isExpanded: false,
        width: DEFAULT_WIDTH,
        height: DEFAULT_HEIGHT,
        x: 0,
        y: 0,
      };
    });
  };

  handleWindowResize = () => {
    const { isExpanded, width, height } = this.state;
    if (isExpanded) {
      const { width: newWidth, height: newHeight } = this.calculateDimensions();
      this.setState({
        width: newWidth,
        height: newHeight,
      });
    } else {
      const maxSafeWidth = this.getMaxAvailableWidth();
      const maxSafeHeight =
        window.innerHeight - (PLAYER_HEIGHT + BUTTON_HEIGHT + PADDING_TOP);
      if (width > maxSafeWidth || height > maxSafeHeight) {
        this.setState({
          width: Math.min(width, maxSafeWidth),
          height: Math.min(height, maxSafeHeight),
        });
      }
    }
  };

  onResize = (event: React.SyntheticEvent, data: ResizeCallbackData) => {
    this.setState({
      width: data.size.width,
      height: data.size.height,
      isExpanded: false,
    });
  };

  onInteractionStart = () => {
    this.setState({ isInteracting: true });
  };

  onInteractionStop = () => {
    this.setState({ isInteracting: false });
  };

  onDrag = (event: DraggableEvent, data: DraggableData) => {
    this.setState({
      x: data.x,
      y: data.y,
    });
  };

  render() {
    const {
      hidePlayer,
      isExpanded,
      width,
      height,
      x,
      y,
      isInteracting,
    } = this.state;

    const options: Options = {
      playerVars: {
        controls: 0,
        showinfo: 0,
        fs: 0,
        iv_load_policy: 3,
        modestbranding: 1,
        rel: 0,
        origin: window.location.origin,
      },
      width: "100%",
      height: "100%",
    };

    const maxAvailableWidth = this.getMaxAvailableWidth();
    const dynamicMaxWidth = Math.min(EXPANDED_WIDTH, maxAvailableWidth);
    const dynamicMaxHeight = Math.min(
      EXPANDED_HEIGHT + BUTTON_HEIGHT,
      window.innerHeight - (PLAYER_HEIGHT + BUTTON_HEIGHT + PADDING_TOP)
    );

    const draggableBoundPadding = 10;
    // width of screen - padding on each side - youtube player width
    const leftBound =
      document.body.clientWidth - draggableBoundPadding * 2 - width;

    const isCurrentDataSource =
      store.get(currentDataSourceNameAtom) === this.name;
    const isPlayerVisible = isCurrentDataSource && !hidePlayer;

    return (
      <Draggable
        handle=".youtube-drag-handle"
        position={{ x, y }}
        disabled={isExpanded || isInteracting}
        cancel=".react-resizable-handle"
        onDrag={this.onDrag}
        onStart={this.onInteractionStart}
        onStop={this.onInteractionStop}
        bounds={{
          left: -leftBound,
          right: -draggableBoundPadding,
          bottom: -draggableBoundPadding,
        }}
      >
        <div
          className={`youtube-wrapper${!isPlayerVisible ? " hidden" : ""}${
            isExpanded ? " expanded" : ""
          }
          `}
          data-testid="youtube-wrapper"
        >
          <button
            className="btn btn-sm youtube-button youtube-drag-handle"
            type="button"
          >
            <FontAwesomeIcon icon={faArrowsAlt} />
          </button>
          <button
            className="btn btn-sm youtube-button"
            type="button"
            onClick={this.handleExpandToggle}
            title={isExpanded ? "Restore size" : "Expand video"}
            aria-label={isExpanded ? "Restore size" : "Expand video"}
          >
            <FontAwesomeIcon icon={isExpanded ? faCompress : faExpand} />
          </button>
          <button
            className="btn btn-sm youtube-button"
            type="button"
            onClick={this.handleHide}
          >
            <FontAwesomeIcon icon={faTimes} />
          </button>
          <ResizableBox
            width={width}
            height={height}
            onResizeStart={this.onInteractionStart}
            onResize={this.onResize}
            onResizeStop={this.onInteractionStop}
            resizeHandles={["nw"]}
            minConstraints={[DEFAULT_WIDTH, DEFAULT_HEIGHT]}
            maxConstraints={[dynamicMaxWidth, dynamicMaxHeight]}
            axis={isExpanded ? "none" : "both"}
            className="youtube-resizable-container"
          >
            <YouTube
              className={`youtube-player${
                isInteracting ? " no-video-interaction" : ""
              }`}
              opts={options}
              onError={this.onError}
              onStateChange={this.handlePlayerStateChanged}
              onReady={this.onReady}
              videoId=""
            />
          </ResizableBox>
        </div>
      </Draggable>
    );
  }
}
