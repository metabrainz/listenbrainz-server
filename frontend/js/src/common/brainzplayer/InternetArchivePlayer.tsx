import React from "react";
import { faArchive } from "@fortawesome/free-solid-svg-icons";
import { DataSourceProps, DataSourceType } from "./BrainzPlayer";
import { getTrackName, getArtistName } from "../../utils/utils";

type IARecording = {
  track_id: string;
  name: string;
  artist: string[];
  album?: string;
  stream_urls: string[];
  artwork_url?: string;
};

type State = {
  loading: boolean;
  currentTrack: IARecording | null;
};

export default class InternetArchivePlayer
  extends React.Component<DataSourceProps, State>
  implements DataSourceType {
  public name = "internetArchive";
  public domainName = "archive.org";
  public icon = faArchive;
  public iconColor = "#6c757d";
  audioRef: React.RefObject<HTMLAudioElement>;

  constructor(props: DataSourceProps) {
    super(props);
    this.audioRef = React.createRef();
    this.state = {
      loading: false,
      currentTrack: null,
    };
  }


  componentDidUpdate(prevProps: DataSourceProps, prevState: State) {
    const { currentTrack } = this.state;
    const { currentTrack: prevCurrentTrack } = prevState;
    if (currentTrack && currentTrack !== prevCurrentTrack) {
      this.playCurrentTrack();
    }
  }

  handleAudioEnded = () => {
    const { onTrackEnd } = this.props;
    onTrackEnd();
  };

  handleTimeUpdate = () => {
    const { onProgressChange } = this.props;
    if (this.audioRef.current) {
      onProgressChange(this.audioRef.current.currentTime * 1000);
    }
  };

  handleLoadedMetadata = () => {
    const { onDurationChange } = this.props;
    if (this.audioRef.current) {
      onDurationChange(this.audioRef.current.duration * 1000);
    }
  };

  searchAndPlayTrack = async (listen: any) => {
    const { onTrackNotFound, handleError } = this.props;
    const trackName = getTrackName(listen);
    const artistName = getArtistName(listen);

    if (!trackName && !artistName) {
      onTrackNotFound();
      return;
    }

    this.setState({ loading: true, currentTrack: null });

    try {
      const params = new URLSearchParams();
      if (trackName) params.append("track", trackName);
      if (artistName) params.append("artist", artistName);

      const response = await fetch(
        `/1/internet_archive/search?${params.toString()}`
      );
      const data = await response.json();

      if (data.results && data.results.length > 0) {
        this.setState({ currentTrack: data.results[0], loading: false });
      } else {
        this.setState({ loading: false, currentTrack: null });
        onTrackNotFound();
      }
    } catch (err) {
      this.setState({ loading: false, currentTrack: null });
      handleError(err, "Internet Archive search error");
      onTrackNotFound();
    }
  };

  playListen = (listen: any) => {
    this.searchAndPlayTrack(listen);
  };

  playCurrentTrack = () => {
    const {
      onPlayerPausedChange,
      onTrackInfoChange,
      onDurationChange,
    } = this.props;
    const { currentTrack } = this.state;
    if (this.audioRef.current && currentTrack) {
      this.audioRef.current.currentTime = 0;
      this.audioRef.current.play();
      onPlayerPausedChange(false);
      onTrackInfoChange(
        currentTrack.name,
        currentTrack.track_id,
        currentTrack.artist.join(", "),
        currentTrack.album,
        currentTrack.artwork_url
          ? [{ src: currentTrack.artwork_url }]
          : undefined
      );
      onDurationChange(this.audioRef.current.duration * 1000 || 0);
    }
  };

  togglePlay = () => {
    const { playerPaused, onPlayerPausedChange } = this.props;
    if (!this.audioRef.current) return;
    if (playerPaused) {
      this.audioRef.current.play();
      onPlayerPausedChange(false);
    } else {
      this.audioRef.current.pause();
      onPlayerPausedChange(true);
    }
  };

  seekToPositionMs = (ms: number) => {
    const { onProgressChange } = this.props;
    if (this.audioRef.current) {
      this.audioRef.current.currentTime = ms / 1000;
      onProgressChange(ms);
    }
  };

  canSearchAndPlayTracks = () => true;

  datasourceRecordsListens = () => false;

  render() {
    const { show, playerPaused } = this.props;
    const { loading, currentTrack } = this.state;
    if (!show) return null;

    return (
      <div className="internet-archive-player">
        {loading && <div>Searching Internet Archive...</div>}
        {currentTrack && (
          <>
            {currentTrack.artwork_url && (
              <img
                src={currentTrack.artwork_url}
                alt={currentTrack.name}
                width={60}
                style={{ marginRight: 10 }}
              />
            )}
            <audio
              ref={this.audioRef}
              src={currentTrack.stream_urls[0]}
              onEnded={this.handleAudioEnded}
              onTimeUpdate={this.handleTimeUpdate}
              onLoadedMetadata={this.handleLoadedMetadata}
              autoPlay={!playerPaused}
            >
              <track kind="captions" />
            </audio>
            <div>
              <strong>{currentTrack.artist.join(", ")}</strong> –{" "}
              {currentTrack.name}
            </div>
          </>
        )}
      </div>
    );
  }
}
