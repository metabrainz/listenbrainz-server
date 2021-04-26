import * as React from "react";
import YouTube, { Options } from "react-youtube";
import {
  isEqual as _isEqual,
  get as _get,
  isNil as _isNil,
  isString as _isString,
} from "lodash";
import { DataSourceType, DataSourceProps } from "./BrainzPlayer";
import { getTrackExtension } from "./playlists/utils";

type YoutubePlayerState = {
  currentListen?: Listen;
};

// For some reason Youtube types do not document getVideoData,
// which we need to determine if there was no search results
type ExtendedYoutubePlayer = {
  getVideoData?: () => { video_id?: string; author: string; title: string };
} & YT.Player;

export default class YoutubePlayer
  extends React.Component<DataSourceProps, YoutubePlayerState>
  implements DataSourceType {
  youtubePlayer?: ExtendedYoutubePlayer;
  checkVideoLoadedTimerId?: NodeJS.Timeout;

  componentDidUpdate(prevProps: DataSourceProps) {
    const { show } = this.props;
    if (prevProps.show === true && show === false && this.youtubePlayer) {
      this.youtubePlayer.stopVideo();
      // Clear playlist
      this.youtubePlayer.cueVideoById("");
    }
  }

  onReady = (event: YT.PlayerEvent): void => {
    this.youtubePlayer = event.target;
  };

  handlePlayerStateChanged = (event: YT.OnStateChangeEvent) => {
    const { data: state, target: player } = event;
    const {
      onPlayerPausedChange,
      onDurationChange,
      onProgressChange,
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
    if (
      state === YouTube.PlayerState.UNSTARTED ||
      state === YouTube.PlayerState.BUFFERING
    ) {
      const { onTrackInfoChange } = this.props;
      const title = _get(player, "playerInfo.videoData.title", "");
      onTrackInfoChange(title);
      player.playVideo();
      onPlayerPausedChange(false);
      onDurationChange(player.getDuration() * 1000);
    }
    if (state === YouTube.PlayerState.PAUSED) {
      onPlayerPausedChange(true);
    }
    if (state === YouTube.PlayerState.PLAYING) {
      onPlayerPausedChange(false);
    }
    onProgressChange(player.getCurrentTime() * 1000);
  };

  searchAndPlayTrack = (listen: Listen | JSPFTrack): void => {
    const trackName =
      _get(listen, "track_metadata.track_name") || _get(listen, "title");
    const artistName =
      _get(listen, "track_metadata.artist_name") || _get(listen, "creator");
    const releaseName = _get(listen, "track_metadata.release_name");
    const { handleWarning, onTrackNotFound } = this.props;
    if (!trackName) {
      handleWarning("Not enough info to search on Youtube");
      onTrackNotFound();
    } else if (this.youtubePlayer) {
      let query = trackName;
      if (artistName) {
        query += ` ${artistName}`;
      }
      if (releaseName) {
        query += ` ${releaseName}`;
      }
      this.youtubePlayer.loadPlaylist({
        list: query,
        listType: "search",
      });
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

  playListen = (listen: Listen | JSPFTrack) => {
    const { show } = this.props;
    if (!show) {
      return;
    }
    let youtubeId = _get(listen, "track_metadata.additional_info.youtube_id");
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (!youtubeId && _isString(originURL) && originURL.length) {
      const parsedURL = new URL(originURL);
      const { hostname, searchParams } = parsedURL;
      if (/youtube\.com/.test(hostname)) {
        youtubeId = searchParams.get("v");
      }
    }
    if (youtubeId) {
      this.playTrackById(youtubeId);
    } else {
      this.searchAndPlayTrack(listen);
    }
    this.checkVideoLoadedTimerId = setTimeout(
      this.checkVideoLoaded.bind(this),
      1500
    );
  };

  checkVideoLoaded = () => {
    if (!this.youtubePlayer) {
      return;
    }
    const { onTrackNotFound } = this.props;
    // We use cueVideoById("") as a means to clear any playlist.
    // If there was an undetected error loading a video, the getVideoData method won't exist
    // or getVideoData.video_id will be null and we should go to the next track
    if (this.youtubePlayer?.getVideoData) {
      const videoData = this.youtubePlayer.getVideoData();
      if (videoData?.video_id === null) {
        onTrackNotFound();
      }
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
          onStateChange={this.handlePlayerStateChanged}
          onError={this.onError}
          onReady={this.onReady}
        />
      </div>
    );
  }
}
