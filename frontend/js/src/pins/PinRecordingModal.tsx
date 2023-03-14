import * as React from "react";
import { get as _get } from "lodash";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import GlobalAppContext from "../utils/GlobalAppContext";
import {
  getArtistName,
  getRecordingMBID,
  getTrackName,
  preciseTimestamp,
} from "../utils/utils";

export type PinRecordingModalProps = {
  recordingToPin: Listen;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
  onSuccessfulPin?: (pinnedrecording: PinnedRecording) => void;
};

export const maxBlurbContentLength = 280;

/** A note about this modal:
 * We use Bootstrap 3 modals, which work with jQuery and data- attributes
 * In order to show the modal properly, including backdrop and visibility,
 * you'll need dataToggle="modal" and dataTarget="#PinRecordingModal"
 * on the buttons that open this modal as well as data-dismiss="modal"
 * on the buttons that close the modal. Modals won't work (be visible) without it
 * until we move to Bootstrap 5 / Bootstrap React which don't require those attributes.
 */

export default NiceModal.create(
  ({ recordingToPin, newAlert, onSuccessfulPin }: PinRecordingModalProps) => {
    const modal = useModal();
    const [blurbContent, setBlurbContent] = React.useState("");

    const { APIService, currentUser } = React.useContext(GlobalAppContext);

    const handleError = React.useCallback(
      (error: string | Error, title?: string): void => {
        if (!error) {
          return;
        }
        newAlert(
          "danger",
          title || "Error",
          typeof error === "object" ? error.message : error
        );
      },
      [newAlert]
    );

    const handleBlurbInputChange = React.useCallback(
      (event: React.ChangeEvent<HTMLTextAreaElement>) => {
        event.preventDefault();
        const input = event.target.value.replace(/\s\s+/g, " "); // remove line breaks and excessive spaces
        if (input.length <= maxBlurbContentLength) {
          setBlurbContent(input);
        }
      },
      []
    );

    const closeModal = () => {
      modal.hide();
      setTimeout(modal.remove, 500);
    };

    const submitPinRecording = React.useCallback(
      async (event: React.MouseEvent<HTMLButtonElement>) => {
        event.preventDefault();
        if (recordingToPin && currentUser?.auth_token) {
          const recordingMSID = _get(
            recordingToPin,
            "track_metadata.additional_info.recording_msid"
          );
          const recordingMBID = getRecordingMBID(recordingToPin);
          let newPin: PinnedRecording;

          try {
            const response = await APIService.submitPinRecording(
              currentUser.auth_token,
              recordingMSID,
              recordingMBID || undefined,
              blurbContent || undefined
            );
            const { data } = response;
            newPin = data;
          } catch (error) {
            handleError(error, "Error while pinning track");
            return;
          }

          newAlert(
            "success",
            `You pinned a track!`,
            `${getArtistName(recordingToPin)} - ${getTrackName(recordingToPin)}`
          );
          if (onSuccessfulPin) {
            onSuccessfulPin(newPin);
          }
          setBlurbContent("");
          closeModal();
        }
      },
      [recordingToPin, blurbContent]
    );

    const { track_name, artist_name } = recordingToPin.track_metadata;

    const unpin_time_ms: number =
      new Date(Date.now()).getTime() + 1000 * 3600 * 24 * 7;

    return (
      <div
        className={`modal fade ${modal.visible ? "in" : ""}`}
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
                Pin This Track to Your Profile
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
                  placeholder="Let your followers know why you are showcasing this track..."
                  value={blurbContent}
                  name="blurb-content"
                  onChange={handleBlurbInputChange}
                  rows={4}
                  style={{ resize: "vertical" }}
                  spellCheck="false"
                />
              </div>
              <small style={{ display: "block", textAlign: "right" }}>
                {blurbContent.length} / {maxBlurbContentLength}
              </small>
              <small>
                Pinning this track will replace any track currently pinned.{" "}
                <br />
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
                onClick={closeModal}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-success"
                onClick={submitPinRecording}
                data-dismiss="modal"
              >
                Pin track
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }
);
