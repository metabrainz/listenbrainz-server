import React from "react";
import { get as _get } from "lodash";
import faInternetArchive from "../icons/faInternetArchive";
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
  currentTrack: IARecording | null;
};

export default class InternetArchivePlayer
  extends React.Component<DataSourceProps, State>
  implements DataSourceType {
  static hasPermissions = () => {
    // Internet Archive doesn't require authentication
    return true;
  };

  static isListenFromThisService(listen: Listen | JSPFTrack): boolean {
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (originURL && typeof originURL === "string") {
      return originURL.includes("archive.org");
    }
    return false;
  }

  static getURLFromListen = (
    listen: Listen | JSPFTrack
  ): string | undefined => {
    const originURL = _get(listen, "track_metadata.additional_info.origin_url");
    if (
      originURL &&
      typeof originURL === "string" &&
      originURL.includes("archive.org")
    ) {
      return originURL;
    }
    return undefined;
  };

  public name = "internetArchive";
  public domainName = "archive.org";
  public icon = faInternetArchive;
  public iconColor = "#6c757d";
  audioRef: React.RefObject<HTMLAudioElement>;

  constructor(props: DataSourceProps) {
    super(props);
    this.audioRef = React.createRef();
    this.state = {
      currentTrack: null,
    };
  }

  componentDidUpdate(prevProps: DataSourceProps) {
    const { show, volume } = this.props;
    if (prevProps.volume !== volume && this.audioRef.current) {
      this.audioRef.current.volume = (volume ?? 100) / 100;
    }

    if (prevProps.show && !show && this.audioRef.current) {
      this.audioRef.current.pause();
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
    const { onTrackNotFound, handleError, handleWarning } = this.props;
    const trackName = getTrackName(listen);
    const artistName = getArtistName(listen);

    if (!trackName && !artistName) {
      handleWarning(
        "We are missing a track title, artist or album name to search on Internet Archive",
        "Not enough info to search on Internet Archive"
      );
      onTrackNotFound();
      return;
    }

    this.setState({ currentTrack: null });

    try {
      const params = new URLSearchParams();
      if (trackName) params.append("track", trackName);
      if (artistName) params.append("artist", artistName);

      const response = await fetch(
        `/1/internet_archive/search?${params.toString()}`
      );
      const data = await response.json();

      if (data.results && data.results.length > 0) {
        // TODO: It might make sense to sanity-check the results to see if the first one is indeed the best match
        // We do something like this in the AppleMusicPlayer with the fuzzysort library
        this.setState({ currentTrack: data.results[0] }, this.playCurrentTrack);
      } else {
        this.setState({ currentTrack: null });
        onTrackNotFound();
      }
    } catch (err) {
      this.setState({ currentTrack: null });
      handleError(err, "Internet Archive search error");
      onTrackNotFound();
    }
  };

  playListen = (listen: any) => {
    this.searchAndPlayTrack(listen);
  };

  playCurrentTrack = async () => {
    const {
      onPlayerPausedChange,
      onTrackInfoChange,
      onDurationChange,
      handleError,
      volume,
    } = this.props;
    const { currentTrack } = this.state;
    if (this.audioRef.current && currentTrack) {
      const [firstUrl] = currentTrack.stream_urls;
      this.audioRef.current.src = firstUrl;
      // Set volume when loading new track
      this.audioRef.current.volume = (volume ?? 100) / 100;
      try {
        await this.audioRef.current.play();
      } catch (error) {
        handleError(error, "Internet Archive playback error");
        return;
      }
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

  togglePlay = async () => {
    const { playerPaused, onPlayerPausedChange, handleError } = this.props;
    if (!this.audioRef.current) return;
    try {
      if (playerPaused) {
        await this.audioRef.current.play();
        onPlayerPausedChange(false);
      } else {
        await this.audioRef.current.pause();
        onPlayerPausedChange(true);
      }
    } catch (error) {
      handleError(error, "Internet Archive playback error");
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
    const { show } = this.props;
    const { currentTrack } = this.state;
    if (!show) return null;

    return (
      <div
        className="internet-archive-player"
        data-testid="internet-archive-player"
      >
        {currentTrack?.artwork_url && (
          <img src={currentTrack.artwork_url} alt={currentTrack.name} />
        )}
        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
        <audio
          ref={this.audioRef}
          onEnded={this.handleAudioEnded}
          onTimeUpdate={this.handleTimeUpdate}
          onDurationChange={this.handleLoadedMetadata}
          autoPlay
          controls={false}
        />
      </div>
    );
  }
}
