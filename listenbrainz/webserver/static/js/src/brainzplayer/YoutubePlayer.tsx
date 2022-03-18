import * as React from "react";
import YouTube, { Options } from "react-youtube";
import {
  isEqual as _isEqual,
  get as _get,
  isNil as _isNil,
  isString as _isString,
  isFunction as _isFunction,
} from "lodash";
import { DataSourceType, DataSourceProps } from "./BrainzPlayer";
import {
  getArtistName,
  getTrackName,
  searchForYoutubeTrack,
} from "../utils/utils";

type YoutubePlayerState = {
  currentListen?: Listen;
};

type YoutubePlayerProps = DataSourceProps & {
  youtubeUser?: YoutubeUser;
  refreshYoutubeToken: () => Promise<string>;
};

// For some reason Youtube types do not document getVideoData,
// which we need to determine if there was no search results
type ExtendedYoutubePlayer = {
  getVideoData?: () => { video_id?: string; author: string; title: string };
} & YT.Player;

export default class YoutubePlayer
  extends React.Component<YoutubePlayerProps, YoutubePlayerState>
  implements DataSourceType {
  static getVideoIDFromListen(listen: Listen | JSPFTrack): string | undefined {
    // Checks if there is a youtube ID in the listen
    // or if the origin_url field contains youtube.com
    const videoURL =
      _get(listen, "track_metadata.additional_info.youtube_id") ??
      _get(listen, "track_metadata.additional_info.origin_url");
    if (_isString(videoURL) && videoURL.length) {
      /** Credit for this regular expression goes to Soufiane Sakhi:
       * https://stackoverflow.com/a/61033353/4904467
       */
      const youtubeURLRegexp = /(?:https?:\/\/)?(?:www\.|m\.)?youtu(?:\.be\/|be.com\/\S*(?:watch|embed)(?:(?:(?=\/[^&\s?]+(?!\S))\/)|(?:\S*v=|v\/)))([^&\s?]+)/g;
      const match = youtubeURLRegexp.exec(videoURL);
      return match?.[1];
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

  static getYoutubeURLFromListen(
    listen: Listen | JSPFTrack
  ): string | undefined {
    // Checks if there is a youtube ID in the listen
    const youtubeId = _get(listen, "track_metadata.additional_info.youtube_id");
    if (youtubeId) {
      return `https://www.youtube.com/watch?v=${youtubeId}`;
    }

    // or if the origin URL contains youtube.com
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (_isString(originURL) && originURL.length) {
      try {
        const parsedURL = new URL(originURL);
        const { hostname, searchParams } = parsedURL;
        if (/youtube\.com/.test(hostname)) {
          return originURL;
        }
      } catch {
        return undefined;
      }
    }
    return undefined;
  }

  public name = "youtube";
  public domainName = "youtube.com";
  youtubePlayer?: ExtendedYoutubePlayer;
  checkVideoLoadedTimerId?: NodeJS.Timeout;

  componentDidUpdate(prevProps: DataSourceProps) {
    const { show } = this.props;
    if (prevProps.show && !show && this.youtubePlayer) {
      this.youtubePlayer.stopVideo();
      // Clear playlist
      this.youtubePlayer.cueVideoById("");
    }
  }

  onReady = (event: YT.PlayerEvent): void => {
    this.youtubePlayer = event.target;
  };

  updateVideoInfo = (): void => {
    let title;
    let images: MediaImage[] = [];
    const { onTrackInfoChange, onDurationChange } = this.props;
    const videoData =
      this.youtubePlayer?.getVideoData && this.youtubePlayer.getVideoData();
    let videoId: string = "";
    if (videoData) {
      title = videoData.title;
      videoId = videoData.video_id as string;
      images = YoutubePlayer.getThumbnailsFromVideoid(videoId);
    } else {
      // Fallback to track name from the listen we are playing
      const { currentListen } = this.state;
      title = getTrackName(currentListen);
    }
    onTrackInfoChange(
      title,
      `https://www.youtube.com/watch?v=${videoId}`,
      undefined,
      undefined,
      images
    );
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
      show,
    } = this.props;
    if (!show) {
      return;
    }
    if (state === YouTube.PlayerState.ENDED) {
      const { onTrackEnd } = this.props;
      onTrackEnd();
      return;
    }
    // New track being played
    if (state === YouTube.PlayerState.UNSTARTED) {
      const title = _get(player, "playerInfo.videoData.title", "");
      const videoId = _get(player, "playerInfo.videoData.video_id", "");
      // The player info is sometimes missing a title initially.
      // We fallback to getting it with getVideoData method once the information is loaded in the player
      if (!title) {
        setTimeout(this.updateVideoInfo.bind(this), 2000);
      } else {
        const images: MediaImage[] = YoutubePlayer.getThumbnailsFromVideoid(
          videoId
        );
        onTrackInfoChange(title, videoId, undefined, undefined, images);
      }
      player.playVideo();
    }
    if (
      state === YouTube.PlayerState.UNSTARTED ||
      state === YouTube.PlayerState.BUFFERING
    ) {
      onPlayerPausedChange(false);
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
        <a href="/profile/music-services/details/" target="_blank">
          link for &quot;playing music&quot; feature
        </a>{" "}
        and refresh this page
      </p>
    );
    const { onTrackNotFound, handleWarning } = this.props;
    handleWarning(errorMessage);
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
      handleWarning("Not enough info to search on Youtube");
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
    const { show } = this.props;
    if (!show) {
      return;
    }
    let youtubeId = _get(listen, "track_metadata.additional_info.youtube_id");
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (!youtubeId && _isString(originURL) && originURL.length) {
      try {
        const parsedURL = new URL(originURL);
        const { hostname, searchParams } = parsedURL;
        if (/youtube\.com/.test(hostname)) {
          youtubeId = searchParams.get("v");
        }
      } catch {
        // URL is not valid, do nothing
      }
    }
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

  render() {
    const { show } = this.props;
    const options: Options = {
      playerVars: {
        autoplay: 1,
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
    return (
      <div className={`youtube ${!show ? "hidden" : ""}`}>
        <YouTube
          opts={options}
          onError={this.onError}
          onStateChange={this.handlePlayerStateChanged}
          onReady={this.onReady}
        />
      </div>
    );
  }
}
