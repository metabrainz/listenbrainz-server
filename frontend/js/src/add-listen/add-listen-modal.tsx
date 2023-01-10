import * as React from "react";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import GlobalAppContext from "../utils/GlobalAppContext";
import SearchDropDown from "./SearchDropDown";
import ListenControl from "../listens/ListenControl";
import SubmitListenInfo from "./submit-listen-info";

type PayloadType = {
  listened_at: number;
  track_metadata: {
    additional_info: {
      release_mbid: string;
      recording_mbid: string;
    };

    artist_name: string;
    track_name: string;
    release_name: string;
  };
};

type TrackType = {
  artist_credit_id: number;
  artist_credit_name: string;
  recording_mbid: string;
  recording_name: string;
  release_mbid: string;
  release_name: string;
};

export interface AddListenModalProps {
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
}

export interface AddListenModalState {
  ListenOption: string;
  SearchField: string;
  TrackResults: Array<TrackType>;
  SelectedTrack: TrackType;
  TrackIsSelected: Boolean;
  TimestampsSubmit: number;
  PayloadArray: Array<PayloadType>;
}

export default class AddListenModal extends React.Component<
  AddListenModalProps,
  AddListenModalState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: AddListenModalProps) {
    super(props);
    this.state = {
      ListenOption: "track",
      SearchField: "",
      TrackResults: [],
      SelectedTrack: {
        artist_credit_id: 0,
        artist_credit_name: "",
        recording_mbid: "",
        recording_name: "",
        release_mbid: "",
        release_name: "",
      },
      TrackIsSelected: false,
      TimestampsSubmit: 0,
      PayloadArray: [],
    };
  }

  componentDidUpdate(pp: any, ps: any, ss: any) {
    const { SearchField } = this.state;
    if (ps.SearchField !== SearchField) {
      this.SearchTrack();
    }
  }

  handleError = (error: string | Error, title?: string): void => {
    const { newAlert } = this.props;
    if (!error) {
      return;
    }
    newAlert(
      "danger",
      title || "Error",
      typeof error === "object" ? error.message : error
    );
  };

  SubmitListen = async () => {
    const { APIService, currentUser } = this.context;
    const { SelectedTrack, TimestampsSubmit } = this.state;
    if (currentUser?.auth_token) {
      this.setState(
        {
          PayloadArray: [
            {
              listened_at: TimestampsSubmit,
              track_metadata: {
                additional_info: {
                  release_mbid: SelectedTrack.release_mbid,
                  recording_mbid: SelectedTrack.recording_mbid,
                },

                artist_name: SelectedTrack.artist_credit_name,
                track_name: SelectedTrack.recording_name,
                release_name: SelectedTrack.release_name,
              },
            },
          ],
        },
        async () => {
          const {PayloadArray} = this.state;
          const payload = PayloadArray;
          try {
            const status = await APIService.submitListens(
              currentUser.auth_token,
              "single",
              payload
            );
            if (status.status === 200) {
              const { newAlert } = this.props;
              newAlert(
                "success",
                "You added the listen",
                `${SelectedTrack.recording_name} - ${SelectedTrack.artist_credit_name}`
              );
            }
            this.setState({
              PayloadArray: [],
            });
          } catch (error) {
            this.handleError(error, "Error while adding a listen");
          }
        }
      );
    }
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

  TrackName = (event: React.ChangeEvent<HTMLInputElement>) => {
    this.setState({
      SearchField: event.target.value,
    });
  };

  DateToUnixTimestamp = (date: number) => {
    this.setState({
      TimestampsSubmit: date,
    });
  };

  addTrackMetadata = (track: TrackType) => {
    this.setState({
      SelectedTrack: track,
      TrackIsSelected: true,
    });
  };

  removeTrack = () => {
    this.setState({
      ListenOption: "track",
      SearchField: "",
      TrackResults: [],
      SelectedTrack: {
        artist_credit_id: 0,
        artist_credit_name: "",
        recording_mbid: "",
        recording_name: "",
        release_mbid: "",
        release_name: "",
      },
      TrackIsSelected: false,
      TimestampsSubmit: 0,
    });
  };

  addAlbum = () => {
    this.setState({
      ListenOption: "album",
      SearchField: "",
      TrackResults: [],
      SelectedTrack: {
        artist_credit_id: 0,
        artist_credit_name: "",
        recording_mbid: "",
        recording_name: "",
        release_mbid: "",
        release_name: "",
      },
      TrackIsSelected: false,
      TimestampsSubmit: 0,
    });
  };

  addTrack = () => {
    this.setState({
      ListenOption: "track",
      SearchField: "",
      TrackResults: [],
      SelectedTrack: {
        artist_credit_id: 0,
        artist_credit_name: "",
        recording_mbid: "",
        recording_name: "",
        release_mbid: "",
        release_name: "",
      },
      TrackIsSelected: false,
      TimestampsSubmit: 0,
    });
  };

  closeModal = () => {
    this.setState({
      ListenOption: "track",
      SearchField: "",
      TrackResults: [],
      SelectedTrack: {
        artist_credit_id: 0,
        artist_credit_name: "",
        recording_mbid: "",
        recording_name: "",
        release_mbid: "",
        release_name: "",
      },
      TrackIsSelected: false,
      TimestampsSubmit: 0,
    });
  };

  render() {
    const {
      ListenOption,
      TrackResults,
      TrackIsSelected,
      SelectedTrack,
      SearchField,
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
                    ListenOption === "track"
                      ? "option-active"
                      : "option-unactive"
                  }`}
                  onClick={this.addTrack}
                >
                  Add track
                </button>
                {/* <button
                  type="button"
                  className={`btn btn-primary add-listen ${
                    ListenOption === "album"
                      ? "option-active"
                      : "option-unactive"
                  }`}
                  onClick={this.addAlbum}
                >
                  Add album
                </button> */}
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
                    <SubmitListenInfo
                      SelectedTrack={SelectedTrack}
                      DateToUnixTimestamp={this.DateToUnixTimestamp}
                    />
                  </div>
                ))}
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-default"
                data-dismiss="modal"
                onClick={this.closeModal}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-success"
                data-dismiss="modal"
                disabled={TrackIsSelected === false}
                onClick={this.SubmitListen}
              >
                Add Listen
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }
}
