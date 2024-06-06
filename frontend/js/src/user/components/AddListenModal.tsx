import React, { useCallback, useContext, useState } from "react";
import DateTimePicker from "react-datetime-picker/dist/entry.nostyle";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCalendar } from "@fortawesome/free-regular-svg-icons";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import { Link } from "react-router-dom";
import { add } from "date-fns";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { convertDateToUnixTimestamp } from "../../utils/utils";
import { ToastMsg } from "../../notifications/Notifications";
import AddSingleListen from "./AddSingleListen";
import AddAlbumListens from "./AddAlbumListens";

enum SubmitListenType {
  "track",
  "album",
}
export type MBTrackWithAC = MusicBrainzTrack & WithArtistCredits;

export function getListenFromRecording(
  recording: MusicBrainzRecordingWithReleases,
  date?: Date,
  release?: MusicBrainzRelease
): Listen {
  const listen: Listen = {
    listened_at: date ? convertDateToUnixTimestamp(date) : 0,
    track_metadata: {
      artist_name:
        recording["artist-credit"]
          ?.map((artist) => `${artist.name}${artist.joinphrase}`)
          .join("") ?? "",
      track_name: recording.title,
      release_mbid: recording.releases[0].id,
      release_name: recording.releases[0].title,
      additional_info: {
        recording_mbid: recording.id,
        submission_client: "listenbrainz web",
        duration_ms: recording.length,
        artist_mbids: recording["artist-credit"].map((ac) => ac.artist.id),
      },
    },
  };
  if (release) {
    listen.track_metadata.release_mbid = release.id;
    listen.track_metadata.release_name = release.title;
  }
  return listen;
}

const getListenFromTrack = (
  track: MusicBrainzTrack & WithArtistCredits,
  date: Date,
  release?: MusicBrainzRelease
): Listen => {
  const listen: Listen = {
    listened_at: convertDateToUnixTimestamp(date),
    track_metadata: {
      track_name: track.title,
      artist_name:
        track["artist-credit"]
          ?.map((artist) => `${artist.name}${artist.joinphrase}`)
          .join("") ?? "",
      additional_info: {
        recording_mbid: track.recording.id,
        submission_client: "listenbrainz web",
        duration_ms: track.length,
        track_mbid: track.id,
        tracknumber: parseInt(track.number, 10),
        artist_mbids: track["artist-credit"].map((ac) => ac.artist.id),
      },
    },
  };
  if (release) {
    listen.track_metadata.release_mbid = release.id;
    listen.track_metadata.release_name = release.title;
  }
  return listen;
};
// Use a default of 4 minutes for the track length if not available in metadata
const DEFAULT_TRACK_LENGTH_SECONDS = 60 * 4;

export default NiceModal.create(() => {
  const modal = useModal();
  const { APIService, currentUser } = useContext(GlobalAppContext);
  const { auth_token } = currentUser;
  const [listenOption, setListenOption] = useState<SubmitListenType>(
    SubmitListenType.track
  );
  const [selectedRecording, setSelectedRecording] = useState<
    MusicBrainzRecordingWithReleases
  >();
  const [selectedAlbumTracks, setSelectedAlbumTracks] = useState<
    MBTrackWithAC[]
  >([]);
  const [selectedRelease, setSelectedRelease] = useState<MusicBrainzRelease>();
  // const [selectedListens, setSelectedListens] = useState<Listen[]>([]);
  const [customTimestamp, setCustomTimestamp] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date());

  const closeModal = useCallback(() => {
    modal.hide();
    document?.body?.classList?.remove("modal-open");
    setTimeout(modal.remove, 200);
  }, [modal]);

  const handleError = useCallback(
    (error: string | Error, title?: string): void => {
      if (!error) {
        return;
      }
      toast.error(
        <ToastMsg
          title={title || "Error"}
          message={typeof error === "object" ? error.message : error.toString()}
        />,
        { toastId: "add-listen-error" }
      );
    },
    []
  );

  const submitListens = useCallback(async () => {
    if (auth_token) {
      let selectedListens;
      let listenType: ListenType;
      // Use the user-selected date, or right now
      const date = customTimestamp ? selectedDate : new Date();
      if (listenOption === SubmitListenType.track) {
        if (!selectedRecording) {
          return;
        }
        listenType = "single";
        selectedListens = [
          getListenFromRecording(selectedRecording, date, selectedRelease),
        ];
      } else {
        if (!selectedAlbumTracks.length) {
          return;
        }
        listenType = "import";
        let cumulativeDateTime = date;
        selectedListens = selectedAlbumTracks.reverse().map((track) => {
          cumulativeDateTime = add(cumulativeDateTime, {
            seconds: -(track.length / 1000 || DEFAULT_TRACK_LENGTH_SECONDS),
          });
          const listen = getListenFromTrack(
            track,
            cumulativeDateTime,
            selectedRelease
          );
          return listen;
        });
      }
      if (selectedListens?.length) {
        try {
          const response = await APIService.submitListens(
            auth_token,
            listenType,
            selectedListens
          );
          await APIService.checkStatus(response);

          toast.success(
            <ToastMsg
              title="Success"
              message={`You added ${selectedListens.length} listens`}
            />,
            { toastId: "added-listens-success" }
          );
          closeModal();
        } catch (error) {
          handleError(error, "Error while submitting listens");
        }
      }
    } else {
      toast.error(
        <ToastMsg
          title="You need to be logged in to submit listens"
          message={<Link to="/login/">Log in here</Link>}
        />,
        { toastId: "auth-error" }
      );
    }
  }, [
    auth_token,
    listenOption,
    selectedRecording,
    selectedAlbumTracks,
    selectedDate,
    customTimestamp,
    selectedRelease,
    APIService,
    closeModal,
    handleError,
  ]);

  return (
    <div
      className={`modal fade ${modal.visible ? "in" : ""}`}
      id="AddListenModal"
      tabIndex={-1}
      role="dialog"
      aria-labelledby="AddListenModalLabel"
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
              onClick={closeModal}
            >
              <span aria-hidden="true">&times;</span>
            </button>
            <h4 className="modal-title" id="AddListenModalLabel">
              Add Listens
            </h4>
          </div>
          <div className="modal-body">
            <div className="add-listen-header">
              <button
                type="button"
                className={`btn btn-primary add-listen ${
                  listenOption === SubmitListenType.track
                    ? "option-active"
                    : "option-inactive"
                }`}
                onClick={() => {
                  setListenOption(SubmitListenType.track);
                }}
              >
                Add track
              </button>
              <button
                type="button"
                className={`btn btn-primary add-listen ${
                  listenOption === SubmitListenType.album
                    ? "option-active"
                    : "option-inactive"
                }`}
                onClick={() => {
                  setListenOption(SubmitListenType.album);
                }}
              >
                Add album
              </button>
            </div>
            {listenOption === SubmitListenType.track && (
              <AddSingleListen
                selectedDate={selectedDate}
                onPayloadChange={setSelectedListens}
              />
            )}
            {listenOption === SubmitListenType.album && (
              <AddAlbumListens
                onPayloadChange={(tracks, release) => {
                  setSelectedAlbumTracks(tracks);
                  setSelectedRelease(release);
                }}
              />
            )}
            <hr />
            <div className="timestamp">
              <h5>Timestamp</h5>
              <div className="timestamp-entities">
                <button
                  type="button"
                  className={`btn btn-primary add-listen ${
                    customTimestamp === false
                      ? "timestamp-active"
                      : "timestamp-inactive"
                  }`}
                  onClick={() => {
                    setCustomTimestamp(false);
                    setSelectedDate(new Date());
                  }}
                >
                  Now
                </button>
                <button
                  type="button"
                  className={`btn btn-primary add-listen ${
                    customTimestamp === true
                      ? "timestamp-active"
                      : "timestamp-inactive"
                  }`}
                  onClick={() => {
                    setCustomTimestamp(true);
                    setSelectedDate(new Date());
                  }}
                >
                  Custom
                </button>
                <div className="timestamp-date-picker">
                  <DateTimePicker
                    value={selectedDate}
                    onChange={(newDateTimePickerValue: Date) => {
                      setSelectedDate(newDateTimePickerValue);
                    }}
                    calendarIcon={
                      <FontAwesomeIcon icon={faCalendar as IconProp} />
                    }
                    maxDate={new Date()}
                    clearIcon={null}
                    format="yyyy-MM-dd h:mm:ss a"
                    disabled={!customTimestamp}
                  />
                </div>
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-default"
              data-dismiss="modal"
              onClick={closeModal}
            >
              Close
            </button>
            <button
              type="submit"
              className="btn btn-success"
              data-dismiss="modal"
              disabled={!selectedAlbumTracks?.length}
              onClick={submitListens}
            >
              Submit {selectedAlbumTracks.length} listen
              {selectedAlbumTracks.length > 1 ? "s" : ""}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
});
