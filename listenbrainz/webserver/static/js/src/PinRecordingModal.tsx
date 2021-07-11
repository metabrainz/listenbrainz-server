import * as React from "react";
import { get as _get } from "lodash";
import GlobalAppContext from "./GlobalAppContext";
import { preciseTimestamp } from "./utils";

export type PinRecordingModalProps = {
  recordingToPin: Listen;
  isCurrentUser: Boolean;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

export interface PinRecordingModalState {
  blurbContent: string;
}

export default class PinRecordingModal extends React.Component<
  PinRecordingModalProps,
  PinRecordingModalState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  readonly maxBlurbContentLength = 280;

  constructor(props: PinRecordingModalProps) {
    super(props);
    this.state = { blurbContent: "" };
  }

  submitPinRecording = async () => {
    const { recordingToPin, isCurrentUser, newAlert } = this.props;
    const { blurbContent } = this.state;
    const { APIService, currentUser } = this.context;

    if (isCurrentUser && currentUser?.auth_token) {
      const recordingMSID = _get(
        recordingToPin,
        "track_metadata.additional_info.recording_msid"
      );
      const recordingMBID = _get(
        recordingToPin,
        "track_metadata.additional_info.recording_mbid"
      );

      try {
        const status = await APIService.submitPinRecording(
          currentUser.auth_token,
          recordingMSID,
          recordingMBID || undefined,
          blurbContent || undefined
        );
        if (status === 200) {
          newAlert(
            "success",
            `You pinned a recording!`,
            `${recordingToPin.track_metadata.artist_name} - ${recordingToPin.track_metadata.track_name}`
          );
          this.setState({ blurbContent: "" });
          window.location.reload();
        }
      } catch (error) {
        this.handleError(error, "Error while pinning recording");
      }
    }
  };

  handleBlurbInputChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    event.preventDefault();
    const input = event.target.value.replace(/\s\s+/g, " "); // remove line breaks and excessive spaces
    if (input.length <= this.maxBlurbContentLength) {
      this.setState({ blurbContent: input });
    }
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
    const { recordingToPin } = this.props;
    const { blurbContent } = this.state;
    const { track_name } = recordingToPin.track_metadata;
    const { artist_name } = recordingToPin.track_metadata;
    const unpin_time_ms: number =
      new Date(Date.now()).getTime() + 1000 * 3600 * 24 * 7;

    return (
      <div
        className="modal fade"
        id="PinRecordingModal"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="PinRecordingModalLabel"
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
              <h4 className="modal-title" id="PinRecordingModalLabel">
                Pin This Recording to Your Profile
              </h4>
            </div>
            <div className="modal-body">
              <p>
                Why do you love{" "}
                <b>
                  {" "}
                  {track_name} by {artist_name}
                </b>
                ? (Optional)
              </p>
              <div className="form-group">
                <textarea
                  className="form-control"
                  id="blurb-content"
                  placeholder="Let your followers know why you are showcasing this recording..."
                  value={blurbContent}
                  name="blurb-content"
                  onChange={this.handleBlurbInputChange}
                  rows={4}
                  style={{ resize: "vertical" }}
                  spellCheck="false"
                />
              </div>
              <small style={{ display: "block", textAlign: "right" }}>
                {blurbContent.length} / {this.maxBlurbContentLength}
              </small>
              <small>
                Pinning this recording will replace any recording currently
                pinned. <br />
                <b>
                  {track_name} by {artist_name}
                </b>{" "}
                will be unpinned from your profile in <b>one week</b>, on{" "}
                {preciseTimestamp(unpin_time_ms, "excludeYear")}.
              </small>
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
                onClick={this.submitPinRecording}
                data-dismiss="modal"
              >
                Pin Recording
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }
}
