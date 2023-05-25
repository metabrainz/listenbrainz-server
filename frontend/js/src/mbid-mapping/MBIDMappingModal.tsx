import * as React from "react";
import { get as _get } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faExchangeAlt,
  faQuestionCircle,
} from "@fortawesome/free-solid-svg-icons";
import Tooltip from "react-tooltip";
import { faTimesCircle } from "@fortawesome/free-regular-svg-icons";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import GlobalAppContext from "../utils/GlobalAppContext";
import {
  getArtistName,
  getRecordingMBID,
  getRecordingMSID,
  getTrackName,
} from "../utils/utils";
import ListenCard from "../listens/ListenCard";
import ListenControl from "../listens/ListenControl";
import { COLOR_LB_LIGHT_GRAY, COLOR_LB_GREEN } from "../utils/constants";
import SearchTrackOrMBID from "../utils/SearchTrackOrMBID";

export type MBIDMappingModalProps = {
  listenToMap?: Listen;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
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

export default NiceModal.create(
  ({ listenToMap, newAlert }: MBIDMappingModalProps) => {
    const modal = useModal();
    const { hide, remove, resolve, visible } = modal;
    const [selectedRecording, setSelectedRecording] = React.useState<
      TrackMetadata
    >();

    const closeModal = React.useCallback(() => {
      hide();
      setTimeout(remove, 500);
    }, [hide, remove]);

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
        newAlert(
          "danger",
          title || "Error",
          typeof error === "object" ? error.message : error
        );
      },
      [newAlert]
    );

    const { APIService, currentUser } = React.useContext(GlobalAppContext);
    const { auth_token } = currentUser;

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

          newAlert(
            "success",
            `You linked a track!`,
            `${getArtistName(listenToMap)} - ${getTrackName(listenToMap)}`
          );
          closeModal();
        }
      },
      [
        listenToMap,
        auth_token,
        newAlert,
        closeModal,
        resolve,
        APIService,
        selectedRecording,
        handleError,
      ]
    );

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
          id="MapToMusicBrainzRecordingModal"
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
              found the album, click on the matching recording (song) in the
              track listing, and copy its URL into the field on this page.
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
                  Listen with a MusicBrainz recording (song). Search by track
                  and artist name or paste a{" "}
                  <a href="https://musicbrainz.org/doc/About">MusicBrainz</a>{" "}
                  recording URL{" "}
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
                  Recordings added to MusicBrainz within the last 4 hours may
                  temporarily look incomplete.
                </small>
                <ListenCard
                  listen={listenToMap}
                  showTimestamp={false}
                  showUsername={false}
                  newAlert={newAlert}
                  // eslint-disable-next-line react/jsx-no-useless-fragment
                  feedbackComponent={<></>}
                  compact
                />
                <div className="text-center mb-10 mt-10">
                  <FontAwesomeIcon
                    icon={faExchangeAlt}
                    rotation={90}
                    size="lg"
                    color={
                      selectedRecording ? COLOR_LB_GREEN : COLOR_LB_LIGHT_GRAY
                    }
                  />
                </div>
                {listenFromSelectedRecording ? (
                  <ListenCard
                    listen={listenFromSelectedRecording}
                    showTimestamp={false}
                    showUsername={false}
                    newAlert={newAlert}
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
                ) : (
                  <div className="card listen-card">
                    <SearchTrackOrMBID
                      onSelectRecording={(trackMetadata) => {
                        setSelectedRecording(trackMetadata);
                      }}
                      newAlert={newAlert}
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
  }
);
