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
import { getArtistName, getTrackName } from "../utils/utils";
import ListenCard from "../listens/ListenCard";
import ListenControl from "../listens/ListenControl";
import { COLOR_LB_LIGHT_GRAY, COLOR_LB_GREEN } from "../utils/constants";

const RECORDING_MBID_RE = /^(https?:\/\/(?:beta\.)?musicbrainz\.org\/recording\/)?([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/i;

export type MBIDMappingModalProps = {
  listenToMap?: Listen;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

function getListenFromSelectedRecording(
  selectedRecording?: MusicBrainzRecording
): Listen | undefined {
  if (!selectedRecording) {
    return undefined;
  }
  return {
    listened_at: 0,
    track_metadata: {
      track_name: selectedRecording.title,
      artist_name: selectedRecording["artist-credit"]
        .map((ac) => ac.name + ac.joinphrase)
        .join(""),
      additional_info: {
        duration_ms: selectedRecording.length,
        artist_mbids: selectedRecording["artist-credit"].map(
          (ac) => ac.artist.id
        ),
        release_artist_names: selectedRecording["artist-credit"].map(
          (ac) => ac.artist.name
        ),
        recording_mbid: selectedRecording.id,
        release_mbid: selectedRecording.releases?.[0]?.id,
      },
    },
  };
}

export default NiceModal.create(
  ({ listenToMap, newAlert }: MBIDMappingModalProps) => {
    const modal = useModal();

    const [recordingMBIDInput, setRecordingMBIDInput] = React.useState("");
    const [recordingMBIDValid, setRecordingMBIDValid] = React.useState(true);
    const [selectedRecording, setSelectedRecording] = React.useState();

    const closeModal = React.useCallback(() => {
      modal.hide();
      setTimeout(modal.remove, 500);
    }, [modal]);

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

    const reset = () => {
      setRecordingMBIDInput("");
      setRecordingMBIDValid(true);
      setSelectedRecording(undefined);
    };

    const { APIService, currentUser } = React.useContext(GlobalAppContext);
    const { auth_token } = currentUser;

    const submitMBIDMapping = React.useCallback(async () => {
      if (listenToMap && recordingMBIDValid && auth_token) {
        const recordingMSID = _get(
          listenToMap,
          "track_metadata.additional_info.recording_msid"
        );
        const recordingMBIDToSubmit = RECORDING_MBID_RE.exec(
          recordingMBIDInput
        )![2].toLowerCase();
        try {
          await APIService.submitMBIDMapping(
            auth_token,
            recordingMSID,
            recordingMBIDToSubmit
          );
        } catch (error) {
          handleError(error, "Error while linking listen");
          return;
        }

        newAlert(
          "success",
          `You linked a track!`,
          `${getArtistName(listenToMap)} - ${getTrackName(listenToMap)}`
        );
        closeModal();
      }
    }, [
      listenToMap,
      auth_token,
      newAlert,
      closeModal,
      APIService,
      recordingMBIDInput,
      recordingMBIDValid,
      handleError,
    ]);

    const handleMBIDInputChange = React.useCallback(
      async (event: React.ChangeEvent<HTMLInputElement>) => {
        event.preventDefault();
        const input = event.target.value;
        const isValidUUID = RECORDING_MBID_RE.test(input);
        const newRecordingMBID = isValidUUID
          ? RECORDING_MBID_RE.exec(input)![2].toLowerCase()
          : "";
        let newSelectedRecording;
        if (isValidUUID) {
          try {
            newSelectedRecording = await APIService.lookupMBRecording(
              newRecordingMBID,
              "artists+releases"
            );
          } catch (error) {
            newAlert(
              "warning",
              "Could not find recording",
              `We could not find a recording on MusicBrainz with the MBID ${newRecordingMBID} ('${error.message}')`
            );
          }
        }
        setRecordingMBIDInput(input);
        setRecordingMBIDValid(isValidUUID);
        setSelectedRecording(newSelectedRecording);
      },
      [APIService, newAlert]
    );

    const listenFromSelectedRecording = getListenFromSelectedRecording(
      selectedRecording
    );
    const isFormInvalid = recordingMBIDInput.length > 0 && !recordingMBIDValid;

    if (!listenToMap) {
      return null;
    }
    return (
      <div
        className="modal fade"
        id="MapToMusicBrainzRecordingModal"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="MBIDMappingModalLabel"
        data-backdrop="static"
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
              <h4 className="modal-title" id="MBIDMappingModalLabel">
                Link this Listen with MusicBrainz
              </h4>
            </div>
            <div className="modal-body">
              <p>
                Sometimes ListenBrainz is unable to automatically link your
                Listen with a MusicBrainz recording (song). Paste a{" "}
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
                      action={reset}
                    />
                  }
                />
              ) : (
                <div className="card listen-card">
                  <div className={isFormInvalid ? "has-error" : ""}>
                    <input
                      type="text"
                      value={recordingMBIDInput}
                      className="form-control"
                      id="recording-mbid"
                      name="recording-mbid"
                      onChange={handleMBIDInputChange}
                      placeholder="MusicBrainz recording URL/MBID"
                      required
                      minLength={36}
                    />
                    {isFormInvalid && (
                      <span
                        className="help-block small"
                        style={{ marginBottom: 0 }}
                      >
                        Not a valid MusicBrainz recording URL or MBID
                      </span>
                    )}
                  </div>
                </div>
              )}
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
                onClick={submitMBIDMapping}
                data-dismiss="modal"
                disabled={!selectedRecording || isFormInvalid}
              >
                Add mapping
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }
);
