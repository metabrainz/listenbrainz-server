import React from "react";
import YouTube, { Options } from "react-youtube";
import { isEqual as _isEqual, get as _get, isNil as _isNil } from "lodash";
import { DataSourceType, DataSourceProps } from "./BrainzPlayer";

type YoutubePlayerState = {
  currentListen?: Listen;
};

enum YoutubePlayerStateType {
  UNSTARTED = -1,
  ENDED = 0,
  PLAYING = 1,
  PAUSED = 2,
  BUFFERING = 3,
  CUED = 5,
}

export default class YoutubePlayer
  extends React.Component<DataSourceProps, YoutubePlayerState>
  implements DataSourceType {
  youtubePlayer: any;
  _firstRun = true;
  youtubePlayerStateTimerID = null;

  // constructor(props: DataSourceProps) {
  //   super(props);
  //   this.state = {
  //     currentListen: undefined,
  //   };
  // }

  componentDidUpdate(prevProps: DataSourceProps) {
    const { show } = this.props;
    if (prevProps.show === true && show === false && this.youtubePlayer) {
      this.youtubePlayer.stopVideo();
      this.youtubePlayer.clearVideo();
    }
  }

  // Youtube component specific methods

  onReady = (event: { target: any }): void => {
    // access to player in all event handlers via event.target
    this.youtubePlayer = event.target;
  };

  // getOptions(): Options {
  //   // const { currentListen } = this.state;
  //   // const { handleWarning, onTrackNotFound } = this.props;
  //   // const trackName = _get(currentListen, "track_metadata.track_name");
  //   // const artistName = _get(currentListen, "track_metadata.artist_name");
  //   // if (!trackName) {
  //   //   handleWarning("Not enough info to search on Youtube");
  //   //   onTrackNotFound();
  //   //   return {};
  //   // }
  //   // let queryString = trackName;
  //   // if (!_isNil(artistName)) {
  //   //   queryString += `+${artistName}`;
  //   // }
  //   return {
  //     playerVars: {
  //       autoplay: 1,
  //       controls: 0,
  //       showinfo: 0,
  //       fs: 0,
  //       iv_load_policy: 3,
  //       // list: queryString,
  //       // listType: "search",
  //       modestbranding: 1,
  //       enablejsapi: 1,
  //       rel: 0,
  //       origin: window.location.origin.toString(),
  //     },
  //   };
  // }

  handlePlayerStateChanged = (event: {
    data: YoutubePlayerStateType;
    target: any;
  }) => {
    const { data: state, target: player } = event;
    const { onPlayerPausedChange, onTrackNotFound, show } = this.props;
    // if (!_get(player, "playerInfo.playlist", []).length) {
    //   onTrackNotFound();
    //   return;
    // }
    // if (!show) {
    //   return;
    // }
    if (state === 0) {
      console.debug("Detected Youtube end of track, playing next track");
      const { onTrackEnd } = this.props;
      onTrackEnd();
    }
    // Unstarted / New track loaded
    if (state === YoutubePlayerStateType.UNSTARTED && show) {
      const { onTrackInfoChange } = this.props;
      const title = _get(player, "playerInfo.videoData.title", "");
      onTrackInfoChange(title);
      player.playVideo();
      onPlayerPausedChange(false);
    }
    // PAUSED
    if (state === YoutubePlayerStateType.PAUSED) {
      onPlayerPausedChange(true);
    }
    // PLAYING
    if (state === YoutubePlayerStateType.PLAYING) {
      onPlayerPausedChange(false);
    }
  };

  searchAndPlayTrack = (listen: Listen): void => {
    const trackName = _get(listen, "track_metadata.track_name");
    const artistName = _get(listen, "track_metadata.artist_name");
    const releaseName = _get(listen, "track_metadata.release_name");
    const { handleWarning, onTrackNotFound } = this.props;
    if (!trackName) {
      handleWarning("Not enough info to search on Youtube");
      onTrackNotFound();
    } else if (this.youtubePlayer) {
      this.youtubePlayer.loadPlaylist({
        list: `${trackName}+${artistName}+${releaseName}`,
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

  playListen = (listen: Listen) => {
    const { show } = this.props;
    if (!show) {
      return;
    }
    // this.setState({ currentListen: listen });
    const youtubeURI = _get(
      listen,
      "track_metadata.additional_info.youtube_id"
    );

    if (youtubeURI) {
      this.playTrackById(youtubeURI);
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
    this.youtubePlayer.seekTo(msTimecode / 1000, false);
    this.youtubePlayer.playVideo();
  };

  onError = (event: { data: any }): void => {
    const { errorNumber } = event.data;
    const { handleError, onTrackNotFound } = this.props;
    handleError(errorNumber);
    onTrackNotFound();
  };

  render() {
    const { show, onTrackNotFound } = this.props;
    const options: Options = {
      playerVars: {
        autoplay: 1,
        controls: 0,
        showinfo: 0,
        fs: 0,
        iv_load_policy: 3,
        modestbranding: 1,
        enablejsapi: 1,
        rel: 0,
        origin: window.location.origin.toString(),
      },
    };
    return (
      <div className={!show ? "hidden" : ""}>
        <YouTube
          opts={options}
          onStateChange={this.handlePlayerStateChanged}
          onReady={this.onReady}
        />
      </div>
    );
  }
}
