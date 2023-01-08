import * as React from "react";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import DatePicker from "react-datepicker";
import GlobalAppContext from "../utils/GlobalAppContext";
import SearchDropDown from "./SearchDropDown";
import ListenControl from "../listens/ListenControl";
import SubmitListenInfo from "./submit-listen-info";

type TrackType = {
  artist_credit_id: number;
  artist_credit_name: string;
  recording_mbid: string;
  recording_name: string;
  release_mbid: string;
  release_name: string;
};

export interface AddListenModalState {
  ListenOption: string;
  SearchField: string;
  TrackResults: Array<TrackType>;
  SelectedTrack: TrackType;
  TrackIsSelected: Boolean;
  TimestampOption: string;
  Timestamp: Date;
}

export default class AddListenModal extends React.Component<
  AddListenModalState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props) {
    super(props);
    this.state = {
      ListenOption: "track",
      SearchField: "",
      TrackResults: [],
      SelectedTrack: {},
      TrackIsSelected: false,
      TimestampOption: "now",
      Timestamp: new Date(),
    };
  }

  closeModal = () => {
    this.setState({
      ListenOption: "track",
      SearchField: "",
      TrackResults: [],
      SelectedTrack: {},
      TrackIsSelected: false,
      TimestampOption: "now",
      Timestamp: new Date(),
    });
  };

  addTrack = () => {
    this.setState({
      ListenOption: "track",
      SearchField: "",
      TrackResults: [],
      SelectedTrack: {},
      TrackIsSelected: false,
      TimestampOption: "now",
      Timestamp: new Date(),
    });
  };

  addAlbum = () => {
    this.setState({
      ListenOption: "album",
      SearchField: "",
      TrackResults: [],
      SelectedTrack: {},
      TrackIsSelected: false,
      TimestampOption: "now",
      Timestamp: new Date(),
    });
  };

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

  TrackName = (event: React.ChangeEvent<HTMLInputElement>) => {
    this.setState({
      SearchField: event.target.value,
    });
  };

  SearchTrack = async () => {
    const { SearchField } = this.state;
    try {
      const response = await fetch(
        "https://labs.api.listenbrainz.org/recording-search/json",
        {
          method: "POST",
          body: JSON.stringify([{ query: SearchField }]),
          headers: {
            "Content-type": "application/json; charset=UTF-8",
          },
        }
      );

      const parsedResponse = await response.json();
      this.setState({
        TrackResults: parsedResponse,
      });
    } catch (error) {
      console.debug(error);
    }
  };

  addTrackMetadata = (track: TrackType) => {
    this.setState({
      SelectedTrack: track,
      TrackIsSelected: true,
    });
  };

  onChangeDateTimePicker = async (newDateTimePickerValue: Date) => {
    this.setState(
      {
        Timestamp: newDateTimePickerValue,
      },
      () => {
        console.log(this.state.Timestamp.toLocaleString("es-CL"));
      }
    );
  };

  removeTrack = () => {
    this.setState({
      ListenOption: "track",
      SearchField: "",
      TrackResults: [],
      SelectedTrack: {},
      TrackIsSelected: false,
      TimestampOption: "now",
      Timestamp: new Date(),
    });
  };

  componentDidUpdate(pp, ps, ss) {
    if (ps.SearchField !== this.state.SearchField) {
      this.SearchTrack();
    }
  }

  render() {
    const {
      ListenOption,
      TrackResults,
      TrackIsSelected,
      SelectedTrack,
      SearchField,
      TimestampOption,
      Timestamp,
    } = this.state;
    return (
      <div
        className="modal fade"
        id="AddListenModal"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="AddListenModalLabel"
        data-backdrop="static"
      >
        <div className="modal-dialog" role="document">
          <form className="modal-content">
            <div className="modal-header">
              <button
                type="button"
                className="close"
                data-dismiss="modal"
                aria-label="Close"
                onClick={this.closeModal}
              >
                <span aria-hidden="true">&times;</span>
              </button>
              <h4 className="modal-title" id="AddListenModalLabel">
                Add Listens
              </h4>
            </div>
            <div className="modal-body">
              <div className="add-listen-header">
                <button
                  type="button"
                  className={`btn btn-primary add-listen ${
                    ListenOption == "track"
                      ? "option-active"
                      : "option-unactive"
                  }`}
                  onClick={this.addTrack}
                >
                  Add track
                </button>
                <button
                  type="button"
                  className={`btn btn-primary add-listen ${
                    ListenOption == "album"
                      ? "option-active"
                      : "option-unactive"
                  }`}
                  onClick={this.addAlbum}
                >
                  Add album
                </button>
              </div>
              {ListenOption === "track" &&
                (TrackIsSelected === false ? (
                  <div>
                    <input
                      type="text"
                      className="form-control add-track-field"
                      onChange={this.TrackName}
                      placeholder="Add Artist name followed by Track name"
                      value={SearchField}
                    />
                    <SearchDropDown
                      TrackResults={TrackResults}
                      action={this.addTrackMetadata}
                    />
                  </div>
                ) : (
                  <div>
                    <div className="addtrackpill">
                      <div>
                        <span>{`${SelectedTrack.recording_name} - ${SelectedTrack.artist_credit_name}`}</span>
                        <ListenControl
                          text=""
                          icon={faTimesCircle}
                          action={this.removeTrack}
                        />
                      </div>
                    </div>
                    <SubmitListenInfo SelectedTrack={SelectedTrack} />
                    <div className="timestamp">
                      <span>Timestamp</span>
                      <button
                        type="button"
                        className={`btn btn-primary add-listen ${
                          TimestampOption == "now"
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
                          TimestampOption == "custom"
                            ? "timestamp-active"
                            : "timestamp-unactive"
                        }`}
                        onClick={this.timestampCustom}
                      >
                        Custom
                      </button>
                    </div>
                    <div className="timestamp-date-picker">
                      {TimestampOption == "custom" ? (
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
                ))}
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-default"
                data-dismiss="modal"
              >
                Cancel
              </button>
              {/* <button
                type="submit"
                className="btn btn-success"
                data-dismiss="modal"
                disabled={users.length === 0}
                onClick={this.submitPersonalRecommendation}
              >
                Send Recommendation
              </button> */}
            </div>
          </form>
        </div>
      </div>
    );
  }
}
