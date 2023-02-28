import * as React from "react";
import { throttle as _throttle } from "lodash";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import DateTimePicker from "react-datetime-picker/dist/entry.nostyle";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCalendar } from "@fortawesome/free-regular-svg-icons";
import ListenControl from "../listens/ListenControl";
import GlobalAppContext from "../utils/GlobalAppContext";
import {
  getAlbumArtFromReleaseMBID,
  convertDateToUnixTimestamp,
} from "../utils/utils";
import ListenCard from "../listens/ListenCard";

enum SubmitListenType {
  "track",
  "album",
}

export interface AddListenModalProps {
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
}

export interface AddListenModalState {
  listenOption: SubmitListenType;
  selectedTrack?: ACRMSearchResult;
  customTimestamp: Boolean;
  selectedDate: Date;
  searchField: string;
  trackResults: Array<ACRMSearchResult>;
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
      listenOption: SubmitListenType.track,
      selectedTrack: undefined,
      customTimestamp: false,
      selectedDate: new Date(),
      searchField: "",
      trackResults: [],
    };
  }

  static getListenFromTrack = (
    selectedDate: Date,
    selectedTrack?: ACRMSearchResult
  ): Listen | undefined => {
    if (!selectedTrack) {
      return undefined;
    }

    return {
      listened_at: convertDateToUnixTimestamp(selectedDate),
      track_metadata: {
        additional_info: {
          release_mbid: selectedTrack.release_mbid,
          recording_mbid: selectedTrack.recording_mbid,
        },

        artist_name: selectedTrack.artist_credit_name,
        track_name: selectedTrack.recording_name,
        release_name: selectedTrack.release_name,
      },
    };
  };

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

  trackMetadata = (track: ACRMSearchResult) => {
    this.setState({
      selectedTrack: track,
    });
  };

  submitListen = async () => {
    const { newAlert } = this.props;
    const { APIService, currentUser } = this.context;
    const { selectedTrack, selectedDate } = this.state;
    if (currentUser?.auth_token) {
      if (selectedTrack) {
        const payload = AddListenModal.getListenFromTrack(
          selectedDate,
          selectedTrack
        );

        if (currentUser.auth_token !== undefined) {
          try {
            if(payload){
            const status = await APIService.submitListens(
              currentUser.auth_token,
              "single",
              [payload]
            );
            if (status.status === 200) {
              newAlert(
                "success",
                "You added the listen",
                `${selectedTrack.recording_name} - ${selectedTrack.artist_credit_name}`
              );
              this.resetTrackSelection();
            }
          }} catch (error) {
            this.handleError(error, "Error while adding a listen");
          }
        }
      }
    } else {
      newAlert(
        "danger",
        "You need to be logged in to Add a Listen",
        <a href="/login">Log in here</a>
      );
    }
  };

  addAlbum = () => {
    this.setState({
      listenOption: SubmitListenType.album,
      selectedTrack: undefined,
    });
  };

  resetTrackSelection = () => {
    this.setState({
      listenOption: SubmitListenType.track,
      selectedTrack: undefined,
    });
  };

  // eslint-disable-next-line react/sort-comp
  throttledSearchTrack = _throttle(async () => {
    await this.searchTrack();
  }, 300);

  searchTrack = async () => {
    const { searchField } = this.state;
    try {
      const response = await fetch(
        "https://labs.api.listenbrainz.org/recording-search/json",
        {
          method: "POST",
          body: JSON.stringify([{ query: searchField }]),
          headers: {
            "Content-type": "application/json; charset=UTF-8",
          },
        }
      );

      const parsedResponse = await response.json();
      this.setState({
        trackResults: parsedResponse,
      });
    } catch (error) {
      console.debug(error);
    }
  };

  trackName = (event: React.ChangeEvent<HTMLInputElement>) => {
    this.setState(
      {
        searchField: event.target.value,
      },
      this.throttledSearchTrack
    );
  };

  timestampNow = () => {
    this.setState({
      customTimestamp: false,
      selectedDate: new Date(),
    });
  };

  timestampCustom = () => {
    this.setState({
      customTimestamp: true,
      selectedDate: new Date(),
    });
  };

  onChangeDateTimePicker = async (newDateTimePickerValue: Date) => {
    const { selectedDate } = this.state;
    this.setState({
      selectedDate: newDateTimePickerValue,
    });
  };

  render() {
    const {
      listenOption,
      selectedTrack,
      searchField,
      trackResults,
      customTimestamp,
      selectedDate,
    } = this.state;

    const { newAlert } = this.props;

    const listenFromSelectedTrack = AddListenModal.getListenFromTrack(
      selectedDate,
      selectedTrack
    );
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
                onClick={this.resetTrackSelection}
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
                    listenOption === SubmitListenType.track
                      ? "option-active"
                      : "option-inactive"
                  }`}
                  onClick={this.resetTrackSelection}
                >
                  Add track
                </button>
              </div>
              {listenOption === SubmitListenType.track &&
                (!selectedTrack ? (
                  <div>
                    <input
                      type="text"
                      className="form-control add-track-field"
                      onChange={this.trackName}
                      placeholder="Search Track"
                      value={searchField}
                    />
                    <div className="track-search-dropdown">
                      {trackResults?.map((track) => {
                        return (
                          <button
                            type="button"
                            onClick={() => this.trackMetadata(track)}
                          >
                            {`${track.recording_name} - ${track.artist_credit_name}`}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="add-track-pill">
                      <div>
                        <span>{`${selectedTrack.recording_name} - ${selectedTrack.artist_credit_name}`}</span>
                        <ListenControl
                          text=""
                          icon={faTimesCircle}
                          action={this.resetTrackSelection}
                        />
                      </div>
                    </div>

                    <div className="track-info">
                      <div style={{ margin: "10px 0px" }}>
                        {listenFromSelectedTrack && (
                          <ListenCard
                            listen={listenFromSelectedTrack}
                            showTimestamp={false}
                            showUsername={false}
                            newAlert={newAlert}
                            // eslint-disable-next-line react/jsx-no-useless-fragment
                            feedbackComponent={<></>}
                            compact
                            additionalActions={
                              <ListenControl
                                buttonClassName="btn-transparent"
                                text=""
                                title="Reset"
                                icon={faTimesCircle}
                                iconSize="lg"
                                action={this.resetTrackSelection}
                              />
                            }
                          />
                        )}
                      </div>
                      <div className="timestamp">
                        <h5>Timestamp</h5>
                        <div className="timestamp-entities">
                          <button
                            type="button"
                            className={`btn btn-primary add-listen ${
                              customTimestamp === false
                                ? "timestamp-active"
                                : "timestamp-inactive"
                            }`}
                            onClick={this.timestampNow}
                          >
                            Now
                          </button>
                          <button
                            type="button"
                            className={`btn btn-primary add-listen ${
                              customTimestamp === true
                                ? "timestamp-active"
                                : "timestamp-inactive"
                            }`}
                            onClick={this.timestampCustom}
                          >
                            Custom
                          </button>
                          <div className="timestamp-date-picker">
                            <DateTimePicker
                              value={selectedDate}
                              onChange={this.onChangeDateTimePicker}
                              calendarIcon={
                                <FontAwesomeIcon
                                  icon={faCalendar as IconProp}
                                />
                              }
                              maxDate={new Date()}
                              clearIcon={null}
                              format="dd/MM/yyyy h:mm:ss a"
                              disabled={!customTimestamp}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-default"
                data-dismiss="modal"
                onClick={this.resetTrackSelection}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-success"
                data-dismiss="modal"
                disabled={!selectedTrack}
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
