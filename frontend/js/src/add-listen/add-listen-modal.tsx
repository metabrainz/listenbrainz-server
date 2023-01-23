import * as React from "react";
import GlobalAppContext from "../utils/GlobalAppContext";
import SubmitListenInfo from "./submit-listen-info";

export interface AddListenModalProps {
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
}

export interface AddListenModalState {
  listenOption: string;
  payloadArray: Array<AddListenPayload>;
  trackDetails: ACRMSearchResult;
  timestampsSubmit: number;
  isTrackReset: Boolean;
  isListenSubmit: Boolean;
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
      listenOption: "track",
      payloadArray: [],
      trackDetails: {
        artist_credit_id: 0,
        artist_credit_name: "",
        recording_mbid: "",
        recording_name: "",
        release_mbid: "",
        release_name: "",
      },
      timestampsSubmit: 0,
      isTrackReset: false,
      isListenSubmit: false,
    };
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

  trackMetadata = (track: ACRMSearchResult) => {
    this.setState({
      trackDetails: track,
    });
  };

  dateToUnixTimestamp = (date: number) => {
    this.setState({
      timestampsSubmit: date,
    });
  };

  SubmitListen = async () => {
    const { APIService, currentUser } = this.context;
    const { trackDetails, timestampsSubmit } = this.state;
    if (currentUser?.auth_token) {
      this.setState(
        {
          payloadArray: [
            {
              listened_at: timestampsSubmit,
              track_metadata: {
                additional_info: {
                  release_mbid: trackDetails.release_mbid,
                  recording_mbid: trackDetails.recording_mbid,
                },

                artist_name: trackDetails.artist_credit_name,
                track_name: trackDetails.recording_name,
                release_name: trackDetails.release_name,
              },
            },
          ],
        },
        async () => {
          const { payloadArray } = this.state;
          const payload = payloadArray;
          if (currentUser.auth_token !== undefined) {
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
                  `${trackDetails.recording_name} - ${trackDetails.artist_credit_name}`
                );
              }
              const { isListenSubmit } = this.state;
              if (isListenSubmit) {
                this.setState({ isListenSubmit: false });
              }
              if (!isListenSubmit) {
                this.setState({ isListenSubmit: true });
              }
              this.setState({
                payloadArray: [],
              });
            } catch (error) {
              this.handleError(error, "Error while adding a listen");
            }
          }
        }
      );
    }
  };

  addAlbum = () => {
    this.setState({
      listenOption: "album",
      payloadArray: [],
      trackDetails: {
        artist_credit_id: 0,
        artist_credit_name: "",
        recording_mbid: "",
        recording_name: "",
        release_mbid: "",
        release_name: "",
      },
      timestampsSubmit: 0,
    });
  };

  resetTrackSelection = () => {
    const { isTrackReset } = this.state;
    this.setState({
      listenOption: "track",
      payloadArray: [],
      trackDetails: {
        artist_credit_id: 0,
        artist_credit_name: "",
        recording_mbid: "",
        recording_name: "",
        release_mbid: "",
        release_name: "",
      },
      timestampsSubmit: 0,
    });
    if (isTrackReset) {
      this.setState({ isTrackReset: false });
    }
    if (!isTrackReset) {
      this.setState({ isTrackReset: true });
    }
  };

  render() {
    const {
      listenOption,
      timestampsSubmit,
      isTrackReset,
      isListenSubmit,
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
                    listenOption === "track"
                      ? "option-active"
                      : "option-unactive"
                  }`}
                  onClick={this.resetTrackSelection}
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
              {listenOption === "track" && (
                <SubmitListenInfo
                  trackMetadata={this.trackMetadata}
                  dateToUnixTimestamp={this.dateToUnixTimestamp}
                  isTrackReset={isTrackReset}
                  isListenSubmit={isListenSubmit}
                />
              )}
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
                disabled={timestampsSubmit === 0}
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
