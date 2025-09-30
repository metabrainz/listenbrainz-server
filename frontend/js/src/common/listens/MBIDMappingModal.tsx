import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { faTimesCircle } from "@fortawesome/free-regular-svg-icons";
import {
  faExchangeAlt,
  faInfoCircle,
  faLink,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import { toast } from "react-toastify";
import Tooltip from "react-tooltip";
import { Link } from "react-router";
import { merge } from "lodash";
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
  const [copyTextClickCounter, setCopyTextClickCounter] = React.useState(0);
  const [selectedRecording, setSelectedRecording] = React.useState<
    TrackMetadata
  >();

  const searchInputRef = React.useRef<SearchInputImperativeHandle>(null);

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
      let resolvedValue: TrackMetadata = selectedRecording;
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
        try {
          // Try to get more metadata for the selected recodring (such as artist mbids)
          const response = await APIService.getRecordingMetadata([
            recordingMBID,
          ]);
          const metadata = response?.[recordingMBID];
          if (metadata) {
            resolvedValue = merge(selectedRecording, {
              artist_name: metadata?.artist?.name,
              additional_info: {
                duration_ms: metadata?.recording?.length,
              },
              mbid_mapping: {
                artist_mbids: metadata?.artist?.artists?.map(
                  (ar) => ar.artist_mbid
                ),
                artists: metadata?.artist?.artists,
                release_mbid: metadata?.release?.mbid,
                caa_id: metadata?.release?.caa_id,
                caa_release_mbid: metadata?.release?.caa_release_mbid,
                year: metadata?.release?.year,
                release_artist_name: metadata?.release?.album_artist_name,
                release_group_mbid: metadata?.release?.release_group_mbid,
              },
            });
          }
        } catch (error) {
          // Ignore this failure, it is only cosmetic
        }
        modal.resolve(resolvedValue);

        toast.success(
          <ToastMsg
            title="You linked a track!"
            message={`${getArtistName(listenToMap)} - ${getTrackName(
              listenToMap
            )}`}
          />,
          { toastId: "linked-track" }
        );
        modal.hide();
      }
    },
    [listenToMap, auth_token, modal, APIService, selectedRecording, handleError]
  );

  const copyTextToSearchField = React.useCallback(() => {
    setCopyTextClickCounter((value) => value + 1);
    setDefaultValue(
      `${getTrackName(listenToMap)} - ${getArtistName(listenToMap)}`
    );
    // Autofocus on the search input in order to automatically show list of results
    searchInputRef?.current?.focus();
  }, [listenToMap]);

  const listenFromSelectedRecording = getListenFromSelectedRecording(
    selectedRecording
  );

  if (!listenToMap) {
    return null;
  }
  return (
    <Modal
      {...bootstrapDialog(modal)}
      title="Link listen"
      aria-labelledby="MBIDMappingModalLabel"
      id="MBIDMappingModal"
    >
      <Modal.Header closeButton>
        <Modal.Title id="MBIDMappingModalLabel">
          Link this listen with{" "}
          <a href="https://musicbrainz.org/doc/About">MusicBrainz</a>
        </Modal.Title>
      </Modal.Header>
      <form className="modal-content" onSubmit={submitMBIDMapping}>
        <Modal.Body>
          <ListenCard
            listen={listenToMap}
            showTimestamp={false}
            showUsername={false}
            // eslint-disable-next-line react/jsx-no-useless-fragment
            feedbackComponent={<></>}
            // eslint-disable-next-line react/jsx-no-useless-fragment
            customThumbnail={<></>}
            compact
          />

          <div className="text-center mb-3 mt-3">
            <button
              type="button"
              className="btn btn-transparent btn-rounded"
              disabled={Boolean(selectedRecording)}
              onClick={copyTextToSearchField}
            >
              <FontAwesomeIcon
                icon={faExchangeAlt}
                rotation={90}
                size="lg"
                color={selectedRecording ? COLOR_LB_GREEN : COLOR_LB_LIGHT_GRAY}
              />
              <div className="text-muted">copy text</div>
            </button>
          </div>

          {listenFromSelectedRecording ? (
            <ListenCard
              listen={listenFromSelectedRecording}
              showTimestamp={false}
              showUsername={false}
              compact
              additionalActions={
                <ListenControl
                  buttonClassName="btn btn-transparent"
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
                ref={searchInputRef}
                expectedPayload="trackmetadata"
                key={`${defaultValue}-${copyTextClickCounter}`}
                onSelectRecording={(trackMetadata) => {
                  setSelectedRecording(trackMetadata);
                }}
                defaultValue={defaultValue}
              />
            </div>
          )}
        </Modal.Body>
        <Modal.Footer
          style={{
            textAlign: "left",
            width: "100%",
            display: "inline-block",
          }}
        >
          <div
            className="mb-3"
            style={{
              display: "flex",
              justifyContent: "space-between",
              width: "100%",
            }}
          >
            <Link
              type="button"
              className="btn btn-info"
              to="/settings/link-listens"
              onClick={modal.hide}
            >
              <span
                className="fa-layers fa-fw"
                style={{ marginRight: "0.5em" }}
              >
                <FontAwesomeIcon icon={faLink} />
                <FontAwesomeIcon
                  icon={faLink}
                  color="#FFFFFFA1"
                  transform="end-5"
                />
                <FontAwesomeIcon
                  icon={faLink}
                  color="#ffffff42"
                  transform="end-10"
                />
              </span>
              &nbsp; Mass-link listens tool
            </Link>
            <div style={{ textAlign: "right" }}>
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
                disabled={!selectedRecording}
              >
                Add mapping
              </button>
            </div>
          </div>
          <div className="small">
            <FontAwesomeIcon icon={faInfoCircle} />
            &nbsp;This will also link your other listens with the same metadata.
          </div>
          <div className="small">
            <FontAwesomeIcon icon={faInfoCircle} />
            &nbsp;
            <a
              href="https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html#user-statistics"
              target="_blank"
              rel="noopener noreferrer"
            >
              How long until my stats reflect the change?
            </a>
          </div>
          <div className="small">
            <FontAwesomeIcon icon={faInfoCircle} />
            &nbsp;
            <a
              href="https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html#mbid-mapper-musicbrainz-metadata-cache"
              target="_blank"
              rel="noopener noreferrer"
            >
              Recordings added within the last 4 hours may temporarily look
              incomplete.
            </a>
          </div>
        </Modal.Footer>
      </form>
    </Modal>
  );
});
