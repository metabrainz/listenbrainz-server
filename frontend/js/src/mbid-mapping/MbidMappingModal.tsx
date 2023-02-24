import * as React from "react";
import { get as _get } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faExchangeAlt,
  faQuestionCircle,
} from "@fortawesome/free-solid-svg-icons";
import Tooltip from "react-tooltip";
import { faTimesCircle } from "@fortawesome/free-regular-svg-icons";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getArtistName, getTrackName } from "../utils/utils";
import ListenCard from "../listens/ListenCard";
import ListenControl from "../listens/ListenControl";
import { COLOR_LB_LIGHT_GRAY, COLOR_LB_GREEN } from "../utils/constants";

const RECORDING_MBID_RE = /^(https?:\/\/(?:beta\.)?musicbrainz\.org\/recording\/)?([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/i;

export type MbidMappingModalProps = {
  listenToMap?: Listen;
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
  selectedRecording?: MusicBrainzRecording;
}

export default class MbidMappingModal extends React.Component<
  MbidMappingModalProps,
  MbidMappingModalState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  static getListenFromSelectedRecording = (
    selectedRecording?: MusicBrainzRecording
  ): Listen | undefined => {
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
  };

  constructor(props: MbidMappingModalProps) {
    super(props);
    this.state = {
      recordingMBIDInput: "",
      recordingMBIDSubmit: "",
      recordingMBIDValid: true,
    };
  }

  reset = () => {
    this.setState({
      recordingMBIDInput: "",
      recordingMBIDSubmit: "",
      recordingMBIDValid: true,
      selectedRecording: undefined,
    });
  };

  submitMbidMapping = async () => {
    const { listenToMap, newAlert } = this.props;
    const { recordingMBIDSubmit } = this.state;
    const { APIService, currentUser } = this.context;

    if (listenToMap && currentUser?.auth_token) {
      const recordingMSID = _get(
        listenToMap,
        "track_metadata.additional_info.recording_msid"
      );

      try {
        await APIService.submitMbidMapping(
          currentUser.auth_token,
          recordingMSID,
          recordingMBIDSubmit
        );
      } catch (error) {
        this.handleError(error, "Error while linking listen");
        return;
      }

      newAlert(
        "success",
        `You linked a track!`,
        `${getArtistName(listenToMap)} - ${getTrackName(listenToMap)}`
      );
      this.setState({
        recordingMBIDInput: "",
        recordingMBIDSubmit: "",
        recordingMBIDValid: true,
      });
    }
  };

  handleMbidInputChange = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const { APIService } = this.context;
    const { newAlert } = this.props;
    event.preventDefault();
    const input = event.target.value;
    const isValidUUID = RECORDING_MBID_RE.test(input);
    const recordingMBIDSubmit = isValidUUID
      ? RECORDING_MBID_RE.exec(input)![2].toLowerCase()
      : "";
    let selectedRecording;
    if (isValidUUID) {
      try {
        selectedRecording = await APIService.lookupMBRecording(
          recordingMBIDSubmit,
          "artists+releases"
        );
      } catch (error) {
        newAlert(
          "warning",
          "Could not find recording",
          `We could not find a recording on MusicBrainz with the MBID ${recordingMBIDSubmit} ('${error.message}')`
        );
      }
    }
    this.setState({
      recordingMBIDInput: input,
      recordingMBIDSubmit,
      recordingMBIDValid: isValidUUID,
      selectedRecording,
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
    const { listenToMap, newAlert } = this.props;
    if (!listenToMap) {
      return null;
    }
    const {
      recordingMBIDInput,
      recordingMBIDValid,
      selectedRecording,
    } = this.state;

    const listenFromSelectedRecording = MbidMappingModal.getListenFromSelectedRecording(
      selectedRecording
    );
    const isFormInvalid = recordingMBIDInput.length > 0 && !recordingMBIDValid;

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
              <h4 className="modal-title" id="MbidMappingModalLabel">
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
                      action={this.reset}
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
                      onChange={this.handleMbidInputChange}
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
                onClick={this.reset}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-success"
                onClick={this.submitMbidMapping}
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
}
