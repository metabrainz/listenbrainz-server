/* eslint-disable react/button-has-type */
/* eslint-disable react/jsx-no-comment-textnodes */
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { faTimesCircle } from "@fortawesome/free-regular-svg-icons";
import {
  faExchangeAlt,
  faInfoCircle,
  faQuestionCircle,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import { toast } from "react-toastify";
import Tooltip from "react-tooltip";
import ListenCard from "./ListenCard";
import ListenControl from "./ListenControl";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import SearchTrackOrMBID from "../../utils/SearchTrackOrMBID";
import { COLOR_LB_GREEN, COLOR_LB_LIGHT_GRAY } from "../../utils/constants";
import {
  getArtistName,
  getRecordingMBID,
  getRecordingMSID,
  getTrackName,
} from "../../utils/utils";

export type MBIDMappingModalProps = {
  listenToMap?: Listen;
};

function getListenFromSelectedRecording(
  selectedRecordingMetadata?: TrackMetadata
): Listen | undefined {
  if (!selectedRecordingMetadata) {
    return undefined;
  }
  return {
    listened_at: 0,
    track_metadata: selectedRecordingMetadata,
  };
}

export default NiceModal.create(({ listenToMap }: MBIDMappingModalProps) => {
  const modal = useModal();
  const { resolve, visible } = modal;
  const [copyTextClickCounter, setCopyTextClickCounter] = React.useState(0);
  const [selectedRecording, setSelectedRecording] = React.useState<
    TrackMetadata
  >();

  const closeModal = React.useCallback(() => {
    modal.hide();
    setTimeout(modal.remove, 200);
  }, [modal]);

  React.useEffect(() => {
    const closeOnEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        closeModal();
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [closeModal]);

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
        { toastId: "linked-track-error" }
      );
    },
    []
  );

  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const { auth_token } = currentUser;
  const [defaultValue, setDefaultValue] = React.useState("");

  const submitMBIDMapping = React.useCallback(
    async (event: React.FormEvent) => {
      if (event) {
        event.preventDefault();
      }
      if (!listenToMap || !selectedRecording || !auth_token) {
        return;
      }
      const selectedRecordingToListen = getListenFromSelectedRecording(
        selectedRecording
      );
      const recordingMBID =
        selectedRecordingToListen &&
        getRecordingMBID(selectedRecordingToListen);
      if (recordingMBID) {
        const recordingMSID = getRecordingMSID(listenToMap);
        try {
          await APIService.submitMBIDMapping(
            auth_token,
            recordingMSID,
            recordingMBID
          );
        } catch (error) {
          handleError(error, "Error while linking listen");
          return;
        }

        resolve(selectedRecording);

        toast.success(
          <ToastMsg
            title="You linked a track!"
            message={`${getArtistName(listenToMap)} - ${getTrackName(
              listenToMap
            )}`}
          />,
          { toastId: "linked-track" }
        );
        closeModal();
      }
    },
    [
      listenToMap,
      auth_token,
      closeModal,
      resolve,
      APIService,
      selectedRecording,
      handleError,
    ]
  );

  const copyTextToSearchField = React.useCallback(() => {
    setCopyTextClickCounter((value) => value + 1);
    setDefaultValue(
      `${getTrackName(listenToMap)} - ${getArtistName(listenToMap)}`
    );
  }, [listenToMap]);

  const listenFromSelectedRecording = getListenFromSelectedRecording(
    selectedRecording
  );

  if (!listenToMap) {
    return null;
  }
  return (
    <>
      <div
        className={`modal fade ${visible ? "in" : ""}`}
        style={visible ? { display: "block" } : {}}
        id="MBIDMappingModal"
        role="dialog"
        aria-labelledby="MBIDMappingModalLabel"
      >
        <div className="modal-dialog" role="document">
          <Tooltip id="musicbrainz-helptext" type="light" multiline>
            Use the MusicBrainz search (musicbrainz.org/search) to search for
            recordings (songs). When you have found the one that matches your
            listen, copy its URL (link) into the field on this page.
            <br />
            You can also search for the album you listened to. When you have
            found the album, click on the matching recording (song) in the track
            listing, and copy its URL into the field on this page.
          </Tooltip>
          <form className="modal-content" onSubmit={submitMBIDMapping}>
            <div className="modal-header">
              <button
                type="button"
                className="close"
                onClick={closeModal}
                aria-label="Close"
              >
                <span aria-hidden="true">&times;</span>
              </button>
              <h4 className="modal-title" id="MBIDMappingModalLabel">
                Link this Listen with MusicBrainz
              </h4>
            </div>
            <div className="modal-body">
              <p>
                Sometimes ListenBrainz is unable to automatically link your
                Listen with a MusicBrainz recording. Search by track and artist
                name or paste a{" "}
                <a href="https://musicbrainz.org/doc/About">MusicBrainz</a>{" "}
                recording URL or MBID{" "}
                <FontAwesomeIcon
                  icon={faQuestionCircle}
                  data-tip
                  data-for="musicbrainz-helptext"
                  size="sm"
                />{" "}
                below to link this Listen, as well as your other Listens with
                the same metadata.
              </p>
              <small className="help-block">
                <FontAwesomeIcon icon={faInfoCircle} />
                &nbsp;
                <a
                  href="https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html#user-statistics"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  How long until my stats reflect the change?
                </a>
              </small>
              <ListenCard
                listen={listenToMap}
                showTimestamp={false}
                showUsername={false}
                // eslint-disable-next-line react/jsx-no-useless-fragment
                feedbackComponent={<></>}
                compact
              />

              <div className="text-center mb-10 mt-10">
                <button
                  className="btn btn-transparent btn-rounded"
                  disabled={Boolean(selectedRecording)}
                  onClick={copyTextToSearchField}
                >
                  <FontAwesomeIcon
                    icon={faExchangeAlt}
                    rotation={90}
                    size="lg"
                    color={
                      selectedRecording ? COLOR_LB_GREEN : COLOR_LB_LIGHT_GRAY
                    }
                  />
                  <div className="text-muted">copy text</div>
                </button>
              </div>

              {listenFromSelectedRecording ? (
                <>
                  <ListenCard
                    listen={listenFromSelectedRecording}
                    showTimestamp={false}
                    showUsername={false}
                    compact
                    additionalActions={
                      <ListenControl
                        buttonClassName="btn-transparent"
                        text=""
                        title="Reset"
                        icon={faTimesCircle}
                        iconSize="lg"
                        action={() => setSelectedRecording(undefined)}
                      />
                    }
                  />
                  <small className="help-block">
                    Recordings added to MusicBrainz within the last 4 hours may
                    temporarily look incomplete.
                    <a
                      href="https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html#mbid-mapper-musicbrainz-metadata-cache"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Click here to learn why.
                    </a>
                  </small>
                </>
              ) : (
                <div className="card listen-card">
                  <SearchTrackOrMBID
                    key={`${defaultValue}-${copyTextClickCounter}`}
                    onSelectRecording={(trackMetadata) => {
                      setSelectedRecording(trackMetadata);
                    }}
                    defaultValue={defaultValue}
                  />
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-default"
                onClick={closeModal}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-success"
                disabled={!selectedRecording}
              >
                Add mapping
              </button>
            </div>
          </form>
        </div>
      </div>
      <div className={`modal-backdrop fade ${visible ? "in" : ""}`} />
    </>
  );
});
