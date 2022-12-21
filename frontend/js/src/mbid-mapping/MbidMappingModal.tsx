import * as React from "react";
import { get as _get } from "lodash";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getArtistName, getTrackName } from "../utils/utils";

export type MbidMappingModalProps = {
  recordingToMap?: Listen;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
  onSuccessfulPin?: (pinnedrecording: PinnedRecording) => void;
};

export interface MbidMappingModalState {
  recordingMBID: string;
}

export default class MbidMappingModal extends React.Component<
  MbidMappingModalProps,
  MbidMappingModalState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: MbidMappingModalProps) {
    super(props);
    this.state = { recordingMBID: "" };
  }

  submitMbidMapping = async () => {
    const { recordingToMap, newAlert, onSuccessfulPin } = this.props;
    const { recordingMBID } = this.state;
    const { APIService, currentUser } = this.context;

    if (recordingToMap && currentUser?.auth_token) {
      const recordingMSID = _get(
        recordingToMap,
        "track_metadata.additional_info.recording_msid"
      );

      try {
        const response = await APIService.submitMbidMapping(
          currentUser.auth_token,
          recordingMSID,
          recordingMBID
        );
        const { data } = response;
      } catch (error) {
        this.handleError(error, "Error while pinning track");
        return;
      }

      newAlert(
        "success",
        `You mapped a track!`,
        `${getArtistName(recordingToMap)} - ${getTrackName(recordingToMap)}`
      );
      this.setState({ recordingMBID: "" });

      // if (onSuccessfulPin) {
      //   onSuccessfulPin(newPin);
      // }
    }
  };

  handleMbidInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    event.preventDefault();
    const input = event.target.value;
    this.setState({ recordingMBID: input });
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

  render() {
    const { recordingToMap } = this.props;
    if (!recordingToMap) {
      return null;
    }
    const { recordingMBID } = this.state;

    return (
      <div
        className="modal fade"
        id="MapToMusicBrainzRecordingModal"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="MbidMappingModalLabel"
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
              >
                <span aria-hidden="true">&times;</span>
              </button>
              <h4 className="modal-title" id="MbidMappingModalLabel">
                Set a Recording MBID for this Listen
              </h4>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <input
                  type="text"
                  value={recordingMBID}
                  className="form-control"
                  id="recording-mbid"
                  name="recording-mbid"
                  onChange={this.handleMbidInputChange}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-default"
                data-dismiss="modal"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-success"
                onClick={this.submitMbidMapping}
                data-dismiss="modal"
              >
                Add mapping
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }
}
