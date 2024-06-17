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
import Pill from "../../components/Pill";

enum SubmitListenType {
  "track",
  "album",
}
export type MBTrackWithAC = MusicBrainzTrack & WithArtistCredits;

export function getListenFromRecording(
  recording: MusicBrainzRecordingWithReleasesAndRGs,
  date?: Date,
  release?: MusicBrainzRelease & WithReleaseGroup
): Listen {
  const releaseOrCanonical = release ?? recording.releases[0];
  const listen: Listen = {
    listened_at: date ? convertDateToUnixTimestamp(date) : 0,
    track_metadata: {
      artist_name:
        recording["artist-credit"]
          ?.map((artist) => `${artist.name}${artist.joinphrase}`)
          .join("") ?? "",
      track_name: recording.title,
      release_name: releaseOrCanonical.title,
      additional_info: {
        release_mbid: releaseOrCanonical.id,
        release_group_mbid: releaseOrCanonical["release-group"].id,
        recording_mbid: recording.id,
        submission_client: "listenbrainz web",
        duration_ms: recording.length,
        artist_mbids: recording["artist-credit"].map((ac) => ac.artist.id),
      },
    },
  };
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
// Use a default of 1 minute for the track length if not available in metadata
export const DEFAULT_TRACK_LENGTH_SECONDS = 60;

export default NiceModal.create(() => {
  const modal = useModal();
  const { APIService, currentUser } = useContext(GlobalAppContext);
  const { auth_token } = currentUser;
  const [listenOption, setListenOption] = useState<SubmitListenType>(
    SubmitListenType.track
  );
  const [selectedRecording, setSelectedRecording] = useState<
    MusicBrainzRecordingWithReleasesAndRGs
  >();
  const [selectedAlbumTracks, setSelectedAlbumTracks] = useState<
    MBTrackWithAC[]
  >([]);
  const [selectedRelease, setSelectedRelease] = useState<
    MusicBrainzRelease & WithReleaseGroup
  >();
  const [customTimestamp, setCustomTimestamp] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [invertTimestamps, setInvertTimestamps] = useState(false);

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
      let payload: Listen[] = [];
      const isSingleListen = listenOption === SubmitListenType.track;
      const listenType: ListenType = isSingleListen ? "single" : "import";
      // Use the user-selected date, default to "now"
      const date = customTimestamp ? selectedDate : new Date();
      if (isSingleListen) {
        if (selectedRecording) {
          const listen = getListenFromRecording(
            selectedRecording,
            date,
            selectedRelease
          );
          payload.push(listen);
        }
      } else {
        let selectedTracks = [...selectedAlbumTracks];
        if (invertTimestamps) {
          selectedTracks = selectedTracks.reverse();
        }
        let cumulativeDateTime = date;
        payload = selectedTracks.map((track) => {
          const timeToAdd = track.length / 1000 || DEFAULT_TRACK_LENGTH_SECONDS;
          // We either use the previous value of cumulativeDateTime,
          // or if inverting listening order directly use the new value newTime
          const newTime = add(cumulativeDateTime, {
            seconds: invertTimestamps ? -timeToAdd : timeToAdd,
          });
          const listen = getListenFromTrack(
            track,
            invertTimestamps ? newTime : cumulativeDateTime,
            selectedRelease
          );
          // Then we assign the new time value for the next iteration
          cumulativeDateTime = newTime;
          return listen;
        });
      }
      if (!payload?.length) {
        return;
      }
      const listenOrListens = payload.length > 1 ? "listens" : "listen";
      try {
        const response = await APIService.submitListens(
          auth_token,
          listenType,
          payload
        );
        await APIService.checkStatus(response);

        toast.success(
          <ToastMsg
            title="Success"
            message={`You added ${payload.length} ${listenOrListens}`}
          />,
          { toastId: "added-listens-success" }
        );
        closeModal();
      } catch (error) {
        handleError(
          error,
          `Error while submitting ${payload.length} ${listenOrListens}`
        );
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
    invertTimestamps,
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
              <Pill
                active={listenOption === SubmitListenType.track}
                onClick={() => {
                  setListenOption(SubmitListenType.track);
                }}
                type="secondary"
              >
                Add track
              </Pill>
              <Pill
                active={listenOption === SubmitListenType.album}
                onClick={() => {
                  setListenOption(SubmitListenType.album);
                }}
                type="secondary"
              >
                Add album
              </Pill>
            </div>
            {listenOption === SubmitListenType.track && (
              <AddSingleListen
                onPayloadChange={(recording, release) => {
                  setSelectedRecording(recording);
                  if (release) {
                    setSelectedRelease(release);
                  }
                }}
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
                <Pill
                  active={customTimestamp === false}
                  onClick={() => {
                    setCustomTimestamp(false);
                    setSelectedDate(new Date());
                  }}
                  type="secondary"
                >
                  Now
                </Pill>
                <Pill
                  active={customTimestamp === true}
                  onClick={() => {
                    setCustomTimestamp(true);
                    setSelectedDate(new Date());
                  }}
                  type="secondary"
                >
                  Custom
                </Pill>
                <div className="timestamp-date-picker">
                  <div>
                    <label htmlFor="starts-at">
                      <input
                        name="invert-timestamp"
                        type="radio"
                        checked={invertTimestamps === false}
                        disabled={!customTimestamp}
                        id="starts-at"
                        aria-label="Set the time of the beginning of the album"
                        onChange={() => {
                          setInvertTimestamps(false);
                        }}
                      />
                      &nbsp;Starts at:
                    </label>
                    <label htmlFor="ends-at">
                      <input
                        name="invert-timestamp"
                        type="radio"
                        checked={invertTimestamps === true}
                        disabled={!customTimestamp}
                        id="ends-at"
                        aria-label="Set the time of the end of the album"
                        onChange={() => {
                          setInvertTimestamps(true);
                        }}
                      />
                      &nbsp;Finishes at:
                    </label>
                  </div>
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
            {listenOption === SubmitListenType.track && (
              <button
                type="submit"
                className="btn btn-success"
                data-dismiss="modal"
                disabled={!selectedRecording}
                onClick={submitListens}
              >
                Submit 1 listen
              </button>
            )}
            {listenOption === SubmitListenType.album && (
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
            )}
          </div>
        </form>
      </div>
    </div>
  );
});
