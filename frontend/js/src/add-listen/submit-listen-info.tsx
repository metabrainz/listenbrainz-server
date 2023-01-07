import * as React from "react";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getAlbumArtFromReleaseMBID } from "../utils/utils";

type TrackType = {
  artist_credit_id: number;
  artist_credit_name: string;
  recording_mbid: string;
  recording_name: string;
  release_mbid: string;
  release_name: string;
};

export type SubmitListenInfoState = {
  thumbnailSrc: string;
};

export type SubmitListenInfoProps = {
  SelectedTrack?: TrackType;
};

export default class SubmitListenInfo extends React.Component<
  SubmitListenInfoProps,
  SubmitListenInfoState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: SubmitListenInfoProps) {
    super(props);

    this.state = {
      thumbnailSrc: "",
    };
  }

  async getCoverArt() {
    const { SelectedTrack } = this.props;
    const albumArtSrc = await getAlbumArtFromReleaseMBID(
      SelectedTrack.release_mbid
    );
    if (albumArtSrc) {
      this.setState({ thumbnailSrc: albumArtSrc });
    }
  }

  componentDidMount(): void {
    this.getCoverArt();
  }

  render() {
    const { thumbnailSrc } = this.state;
    const { SelectedTrack } = this.props;

    if (thumbnailSrc != "") {
      return (
        <div className="track-info">
          <div className="cover-art-img">
            <img
              src={thumbnailSrc}
              alt={SelectedTrack?.release_name ?? "cover art"}
            />
          </div>
          <div style={{ display: "block", width: "100%" }}>
            <div className="track-details" style={{ marginTop: "23px" }}>
              <div className="listen-entity">
                <span>Track</span>
              </div>
              <div className="entity-details">
                <span>{`${SelectedTrack?.recording_name}`}</span>
              </div>
            </div>
            <div className="track-details">
              <div className="listen-entity">
                <span>Artist</span>
              </div>
              <div className="entity-details">
                <span>{`${SelectedTrack?.artist_credit_name}`}</span>
              </div>
            </div>
            <div className="track-details">
              <div className="listen-entity">
                <span>Album</span>
              </div>
              <div className="entity-details">
                <span>{`${SelectedTrack?.release_name}`}</span>
              </div>
            </div>
          </div>
        </div>
      );
    }
  }
}
