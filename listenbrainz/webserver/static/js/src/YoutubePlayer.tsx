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
import { searchForYoutubeTrack } from "./utils";

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
    const trackName =
      _get(listen, "track_metadata.track_name") || _get(listen, "title");
    const artistName =
      _get(listen, "track_metadata.artist_name") || _get(listen, "creator");
    const releaseName = _get(listen, "track_metadata.release_name");

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
    if (!trackName) {
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
        this.youtubePlayer.loadPlaylist(videoIds.slice(0, 1));
      } else {
        onTrackNotFound();
      }
    } catch (error) {
      handleWarning(error, "Youtube player error");
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

  isListenFromThisService = (listen: Listen | JSPFTrack): boolean => {
    // Checks if there is a youtube ID in the listen
    const youtubeId = _get(listen, "track_metadata.additional_info.youtube_id");
    if (youtubeId) {
      return true;
    }

    // or if the origin URL contains youtube.com
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (_isString(originURL) && originURL.length) {
      const parsedURL = new URL(originURL);
      const { hostname, searchParams } = parsedURL;
      if (/youtube\.com/.test(hostname)) {
        return true;
      }
    }

    return false;
  };

  canSearchAndPlayTracks = (): boolean => {
    const { youtubeUser } = this.props;
    // check if the user is authed to search with the Youtube API
    return Boolean(youtubeUser) && Boolean(youtubeUser?.api_key);
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
