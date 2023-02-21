import * as React from "react";
import { get as _get } from "lodash";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getArtistName, getTrackName } from "../utils/utils";

const RECORDING_MBID_RE = /^(https?:\/\/(?:beta\.)?musicbrainz\.org\/recording\/)?([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/i;

export type MbidMappingModalProps = {
  recordingToMap?: Listen;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

export interface MbidMappingModalState {
  // Managed form field
  recordingMBIDInput: string;
  // If the input is valid, the extracted UUID
  recordingMBIDSubmit: string;
  recordingMBIDValid: boolean;
}

export default class MbidMappingModal extends React.Component<
  MbidMappingModalProps,
  MbidMappingModalState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: MbidMappingModalProps) {
    super(props);
    this.state = {
      recordingMBIDInput: "",
      recordingMBIDSubmit: "",
      recordingMBIDValid: true,
    };
  }

  submitMbidMapping = async () => {
    const { recordingToMap, newAlert } = this.props;
    const { recordingMBIDSubmit } = this.state;
    const { APIService, currentUser } = this.context;

    if (recordingToMap && currentUser?.auth_token) {
      const recordingMSID = _get(
        recordingToMap,
        "track_metadata.additional_info.recording_msid"
      );

      try {
        await APIService.submitMbidMapping(
          currentUser.auth_token,
          recordingMSID,
          recordingMBIDSubmit
        );
      } catch (error) {
        this.handleError(error, "Error while linking track");
        return;
      }

      newAlert(
        "success",
        `You linked a track!`,
        `${getArtistName(recordingToMap)} - ${getTrackName(recordingToMap)}`
      );
      this.setState({
        recordingMBIDInput: "",
        recordingMBIDSubmit: "",
        recordingMBIDValid: true,
      });
    }
  };

  handleMbidInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    event.preventDefault();
    const input = event.target.value;
    const isValidUUID = RECORDING_MBID_RE.test(input);
    const recordingMBIDSubmit = isValidUUID
      ? RECORDING_MBID_RE.exec(input)![2].toLowerCase()
      : "";
    this.setState({
      recordingMBIDInput: input,
      recordingMBIDSubmit,
      recordingMBIDValid: isValidUUID,
    });
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
    const { recordingMBIDInput, recordingMBIDValid } = this.state;

    const trackName = getTrackName(recordingToMap);
    const artistName = getArtistName(recordingToMap);

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
                Link this Listen with MusicBrainz
              </h4>
            </div>
            <div className="modal-body">
              <p>
                If ListenBrainz was unable to link your Listen to a MusicBrainz
                recording, you can do so manually here. Paste a Recording MBID
                to link it to this Listen and all others with the same metadata.
              </p>

              <p className="modal-track">{trackName}</p>
              <p className="modal-artist">{artistName}</p>

              <div className="form-group">
                <input
                  type="text"
                  value={recordingMBIDInput}
                  className="form-control"
                  id="recording-mbid"
                  name="recording-mbid"
                  onChange={this.handleMbidInputChange}
                />
              </div>
              {recordingMBIDInput.length > 0 && !recordingMBIDValid && (
                <div className="has-error small">
                  Not a valid recording MBID
                </div>
              )}
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
                disabled={!recordingMBIDValid}
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
