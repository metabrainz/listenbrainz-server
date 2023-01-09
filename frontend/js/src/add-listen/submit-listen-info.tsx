import * as React from "react";
import DatePicker from "react-datepicker";
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
  TimestampOption: string;
  Timestamp: Date;
};

export type SubmitListenInfoProps = {
  SelectedTrack: TrackType;
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
      thumbnailSrc: "/static/img/cover-art-placeholder.jpg",
      TimestampOption: "now",
      Timestamp: new Date(),
    };
  }

  componentDidMount(): void {
    this.getCoverArt();
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

  timestampNow = () => {
    this.setState({
      TimestampOption: "now",
      Timestamp: new Date(),
    });
  };

  timestampCustom = () => {
    this.setState({
      TimestampOption: "custom",
      Timestamp: new Date(),
    });
  };

  onChangeDateTimePicker = async (newDateTimePickerValue: Date) => {
    this.setState({
      Timestamp: newDateTimePickerValue,
    });
  };

  render() {
    const { thumbnailSrc, TimestampOption, Timestamp } = this.state;
    const { SelectedTrack } = this.props;

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
          <div className="timestamp">
            <span>Timestamp</span>
            <button
              type="button"
              className={`btn btn-primary add-listen ${
                TimestampOption === "now"
                  ? "timestamp-active"
                  : "timestamp-unactive"
              }`}
              onClick={this.timestampNow}
            >
              Now
            </button>
            <button
              type="button"
              className={`btn btn-primary add-listen ${
                TimestampOption === "custom"
                  ? "timestamp-active"
                  : "timestamp-unactive"
              }`}
              onClick={this.timestampCustom}
            >
              Custom
            </button>
          </div>
          <div className="timestamp-date-picker">
            {TimestampOption === "custom" ? (
              <DatePicker
                selected={Timestamp}
                onChange={this.onChangeDateTimePicker}
                showTimeSelect
                timeFormat="HH:mm"
                timeIntervals={1}
                timeCaption="time"
                dateFormat="dd-MM-yyyy, hh:mm:ss"
              />
            ) : (
              <div className="react-datepicker__input-container">
                <input
                  type="text"
                  value={Timestamp.toLocaleString("es-CL")}
                  readOnly
                />
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }
}
