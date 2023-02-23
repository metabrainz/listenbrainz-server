import * as React from "react";
import { get as _get } from "lodash";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getArtistName, getTrackName } from "../utils/utils";
import ListenCard from "../listens/ListenCard";

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

  constructor(props: MbidMappingModalProps) {
    super(props);
    this.state = {
      recordingMBIDInput: "",
      recordingMBIDSubmit: "",
      recordingMBIDValid: true,
    };
  }

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
        this.handleError(error, "Error while linking track");
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
          recordingMBIDSubmit
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

  getListenFromSelectedRecording = (): Listen | undefined => {
    const { selectedRecording } = this.state;
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
        },
      },
    };
  };

  render() {
    const { listenToMap, newAlert } = this.props;
    if (!listenToMap) {
      return null;
    }
    const { recordingMBIDInput, recordingMBIDValid } = this.state;

    const trackName = getTrackName(recordingToMap);
    const artistName = getArtistName(recordingToMap);
    const listenFromSelectedRecording = this.getListenFromSelectedRecording();

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

              <p>
                Linking: {trackName} — {artistName}
              </p>

              <div className="form-group">
                <input
                  type="text"
                  value={recordingMBIDInput}
                  className="form-control"
                  id="recording-mbid"
                  name="recording-mbid"
                  onChange={this.handleMbidInputChange}
                  required
                  minLength={36}
                />
              </div>
              {recordingMBIDInput.length > 0 && !recordingMBIDValid && (
                <div className="has-error small">
                  Not a valid recording MBID
                </div>
              )}
              {listenFromSelectedRecording && (
                <ListenCard
                  listen={listenFromSelectedRecording}
                  showTimestamp={false}
                  showUsername={false}
                  newAlert={newAlert}
                  // eslint-disable-next-line react/jsx-no-useless-fragment
                  customThumbnail={<></>}
                  compact
                />
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
