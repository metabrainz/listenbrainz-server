import * as React from "react";
import { get as _get } from "lodash";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { toast } from "react-toastify";
import GlobalAppContext from "../utils/GlobalAppContext";
import {
  getArtistName,
  getRecordingMBID,
  getTrackName,
  preciseTimestamp,
} from "../utils/utils";
import { ToastMsg } from "../notifications/Notifications";

export type PinRecordingModalProps = {
  recordingToPin: Listen;
  onSuccessfulPin?: (pinnedrecording: PinnedRecording) => void;
  rowId?: number;
  initialBlurbContent?: string | null;
};

export const maxBlurbContentLength = 280;

export default NiceModal.create(
  ({
    recordingToPin,
    onSuccessfulPin,
    rowId,
    initialBlurbContent,
  }: PinRecordingModalProps) => {
    const modal = useModal();
    const [blurbContent, setBlurbContent] = React.useState(
      initialBlurbContent ?? ""
    );

    const { APIService, currentUser } = React.useContext(GlobalAppContext);

    const isCurrentUser = recordingToPin?.user_name === currentUser?.name;
    const isUpdate = Boolean(rowId) && isCurrentUser;

    const handleError = React.useCallback(
      (error: string | Error, title?: string): void => {
        if (!error) {
          return;
        }
        toast.error(
          <ToastMsg
            title={title || "Error"}
            message={typeof error === "object" ? error.message : error}
          />,
          { toastId: "modal-error" }
        );
      },
      []
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
            toast.success(
              <ToastMsg
                title="You pinned a track!"
                message={`${getArtistName(recordingToPin)} - ${getTrackName(
                  recordingToPin
                )}`}
              />,
              {
                toastId: "pin-track-success",
              }
            );
          } catch (error) {
            handleError(error, "Error while pinning track");
            return;
          }
          if (onSuccessfulPin) {
            onSuccessfulPin(newPin);
          }
          setBlurbContent("");
          modal.hide();
        }
      },
      [
        recordingToPin,
        currentUser.auth_token,
        onSuccessfulPin,
        modal,
        APIService,
        blurbContent,
        handleError,
      ]
    );
    const updatePinnedRecordingComment = React.useCallback(
      async (event: React.MouseEvent<HTMLButtonElement>) => {
        event.preventDefault();
        try {
          if (
            rowId &&
            recordingToPin &&
            currentUser?.auth_token &&
            isCurrentUser
          ) {
            await APIService.updatePinRecordingBlurbContent(
              currentUser.auth_token,
              rowId,
              blurbContent
            );
            toast.success(<ToastMsg title="Comment updated" message="" />, {
              toastId: "pin-update-success",
            });
            modal.resolve(blurbContent);
          }
        } catch (error) {
          handleError(error, "Error while updating pinned recording");
        }
      },
      [
        rowId,
        recordingToPin,
        currentUser.auth_token,
        isCurrentUser,
        APIService,
        blurbContent,
        modal,
        handleError,
      ]
    );
    const { track_name, artist_name } = recordingToPin.track_metadata;

    const unpin_time_ms: number =
      new Date(Date.now()).getTime() + 1000 * 3600 * 24 * 7;

    return (
      <Modal
        {...bootstrapDialog(modal)}
        id="PinRecordingModal"
        title="Pin this track"
        aria-labelledby="PinRecordingModalLabel"
      >
        <Modal.Header closeButton>
          <Modal.Title id="PinRecordingModalLabel">
            Pin this track to your profile
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>
            Why do you love{" "}
            <b>
              {" "}
              {track_name} by {artist_name}
            </b>
            ? (Optional)
          </p>
          <div className="mb-4">
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
            Pinning this track will replace any track currently pinned. <br />
            <b>
              {track_name} by {artist_name}
            </b>{" "}
            will be unpinned from your profile in <b>one week</b>, on{" "}
            {preciseTimestamp(unpin_time_ms, "excludeYear")}.
          </small>
        </Modal.Body>
        <Modal.Footer>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={modal.hide}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-success"
            onClick={
              isUpdate ? updatePinnedRecordingComment : submitPinRecording
            }
          >
            {isUpdate ? "Update comment" : "Pin track"}
          </button>
        </Modal.Footer>
      </Modal>
    );
  }
);
