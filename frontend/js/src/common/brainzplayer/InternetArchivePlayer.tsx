import React from "react";
import { faArchive } from "@fortawesome/free-solid-svg-icons";
import { DataSourceProps, DataSourceType } from "./BrainzPlayer";

// Hardcoded track for now
const HARDCODED_TRACK = {
  track_id: "https://archive.org/details/00TtuloInttrprete66",
  name:
    "Los Norteños / Cuando Canta La Lluvia - Perez Prado y Hermanas Montoya (Very Rare Recordings)",
  artist: ["Pérez Prado y Orquesta con Hermanas Montoya"],
  album: "RCA Victor #70-9428",
  stream_urls: [
    "https://archive.org/download/00TtuloInttrprete66/Cuando%20Canta%20La%20Lluvia.m4a",
    "https://archive.org/download/00TtuloInttrprete66/Cuando%20Canta%20La%20Lluvia.mp3",
  ],
  artwork_url:
    "https://archive.org/download/00TtuloInttrprete66/Cuando%20Canta%20La%20Lluvia.png",
};

export default class InternetArchivePlayer
  extends React.Component<DataSourceProps>
  implements DataSourceType {
  public name = "internetArchive";
  public domainName = "archive.org";
  public icon = faArchive;
  public iconColor = "#6c757d";
  audioRef: React.RefObject<HTMLAudioElement>;

  constructor(props: DataSourceProps) {
    super(props);
    this.audioRef = React.createRef();
  }

  playListen = () => {
    const {
      onPlayerPausedChange,
      onTrackInfoChange,
      onDurationChange,
    } = this.props;
    if (this.audioRef.current) {
      this.audioRef.current.currentTime = 0;
      this.audioRef.current.play();
      onPlayerPausedChange(false);
      onTrackInfoChange(
        HARDCODED_TRACK.name,
        HARDCODED_TRACK.track_id,
        HARDCODED_TRACK.artist.join(", "),
        HARDCODED_TRACK.album,
        [{ src: HARDCODED_TRACK.artwork_url }]
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

  canSearchAndPlayTracks = () => false; // For now, no search

  datasourceRecordsListens = () => false;

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

  render() {
    const { show, playerPaused } = this.props;
    if (!show) return null;
    return (
      <div className="internet-archive-player">
        <img
          src={HARDCODED_TRACK.artwork_url}
          alt={HARDCODED_TRACK.name}
          width={60}
          style={{ marginRight: 10 }}
        />
        <audio
          ref={this.audioRef}
          src={HARDCODED_TRACK.stream_urls[0]}
          onEnded={this.handleAudioEnded}
          onTimeUpdate={this.handleTimeUpdate}
          onLoadedMetadata={this.handleLoadedMetadata}
          autoPlay={!playerPaused}
        >
          <track kind="captions" />
        </audio>
        <div>
          <strong>{HARDCODED_TRACK.artist.join(", ")}</strong> –{" "}
          {HARDCODED_TRACK.name}
        </div>
      </div>
    );
  }
}
