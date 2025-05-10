import React, { useCallback, useContext, useState } from "react";
import DateTimePicker from "react-datetime-picker/dist/entry.nostyle";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCalendar } from "@fortawesome/free-regular-svg-icons";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import { Link } from "react-router-dom";
import { add } from "date-fns";
import { get } from "lodash";
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
      release_name: releaseOrCanonical?.title,
      additional_info: {
        release_mbid: releaseOrCanonical?.id,
        release_group_mbid: releaseOrCanonical?.["release-group"]?.id,
        recording_mbid: recording.id,
        submission_client: "listenbrainz web",
        artist_mbids: recording["artist-credit"].map((ac) => ac.artist.id),
      },
    },
  };
  if (recording.length) {
    // Cannot send a `null` duration
    listen.track_metadata.additional_info!.duration_ms = recording.length;
  }
  return listen;
}

export const getListenFromTrack = (
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
        track_mbid: track.id,
        tracknumber: track.number,
        artist_mbids: track["artist-credit"].map((ac) => ac.artist.id),
      },
    },
  };
  if (track.length) {
    // Cannot send a `null` duration
    listen.track_metadata.additional_info!.duration_ms = track.length;
  } else if (track.recording.length) {
    // Cannot send a `null` duration
    listen.track_metadata.additional_info!.duration_ms = track.recording.length;
  }
  if (release) {
    listen.track_metadata.additional_info!.release_mbid = release.id;
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
  const [selectedListens, setSelectedListens] = useState<Listen[]>([]);
  const [customTimestamp, setCustomTimestamp] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [invertOrder, setInvertOrder] = useState(false);
  const [keepModalOpen, setKeepModalOpen] = useState(false);
  // Used for the automatic switching and search trigger if pasting URL for another entity type
  const [textToSearch, setTextToSearch] = useState<string>();

  const closeModal = useCallback(() => {
    modal.hide();
    document?.body?.classList?.remove("modal-open");
    const backdrop = document?.querySelector(".modal-backdrop");
    if (backdrop) {
      backdrop.remove();
    }
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
      const listenType: ListenType =
        selectedListens?.length <= 1 ? "single" : "import";
      // Use the user-selected date, default to "now"
      const date = customTimestamp ? selectedDate : new Date();
      if (selectedListens?.length) {
        let orderedSelectedListens = [...selectedListens];
        if (invertOrder) {
          orderedSelectedListens = orderedSelectedListens.reverse();
        }
        let cumulativeDateTime = date;
        payload = orderedSelectedListens.map((listen) => {
          // Now we need to set the listening time for each listen
          const modifiedListen = { ...listen };
          const durationMS = get(
            modifiedListen,
            "track_metadata.additional_info.duration_ms"
          );
          const timeToAdd =
            (durationMS && durationMS / 1000) ??
            modifiedListen.track_metadata.additional_info?.duration ??
            DEFAULT_TRACK_LENGTH_SECONDS;
          // We either use the previous value of cumulativeDateTime,
          // or if inverting listening order directly use the new value newTime
          const newTime = add(cumulativeDateTime, {
            seconds: invertOrder ? -timeToAdd : timeToAdd,
          });
          if (invertOrder) {
            modifiedListen.listened_at = convertDateToUnixTimestamp(newTime);
          } else {
            modifiedListen.listened_at = convertDateToUnixTimestamp(
              cumulativeDateTime
            );
          }
          // Then we assign the new time value for the next iteration
          cumulativeDateTime = newTime;
          return modifiedListen;
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

        if (!keepModalOpen) {
          closeModal();
        } else {
          // Reset the form state but keep the modal open
          setSelectedListens([]);
          setTextToSearch("");
        }
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
    selectedListens,
    customTimestamp,
    selectedDate,
    invertOrder,
    APIService,
    closeModal,
    handleError,
    keepModalOpen,
  ]);

  const switchMode = React.useCallback(
    (pastedURL: string) => {
      if (listenOption === SubmitListenType.track) {
        setListenOption(SubmitListenType.album);
      } else if (listenOption === SubmitListenType.album) {
        setListenOption(SubmitListenType.track);
      }
      setTimeout(() => {
        // Trigger search in the inner (grandchild) search input component by modifying the textToSearch prop in child component
        // Give it some time to allow re-render and trigger search in the correct child component
        setTextToSearch(pastedURL);
      }, 200);
      setTimeout(() => {
        // Reset text trigger
        setTextToSearch("");
      }, 500);
    },
    [listenOption]
  );

  const userLocale = navigator.languages?.length
    ? navigator.languages[0]
    : navigator.language;

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
                onPayloadChange={setSelectedListens}
                switchMode={switchMode}
                initialText={textToSearch}
              />
            )}
            {listenOption === SubmitListenType.album && (
              <AddAlbumListens
                onPayloadChange={setSelectedListens}
                switchMode={switchMode}
                initialText={textToSearch}
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
                        checked={invertOrder === false}
                        id="starts-at"
                        aria-label="Set the time of the beginning of the album"
                        onChange={() => {
                          setInvertOrder(false);
                        }}
                      />
                      &nbsp;Starts at:
                    </label>
                    <label htmlFor="ends-at">
                      <input
                        name="invert-timestamp"
                        type="radio"
                        checked={invertOrder === true}
                        id="ends-at"
                        aria-label="Set the time of the end of the album"
                        onChange={() => {
                          setInvertOrder(true);
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
                    format={userLocale ? undefined : "yyyy-MM-dd hh:mm:ss"}
                    locale={userLocale}
                    maxDetail="second"
                    disabled={!customTimestamp}
                  />
                </div>
              </div>
            </div>
          </div>
          <div
            className="modal-footer"
            style={{ display: "flex", alignItems: "center", gap: "1rem" }}
          >
            <div style={{ flex: 1 }}>
              <label style={{ userSelect: "none", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={keepModalOpen}
                  onChange={(e) => setKeepModalOpen(e.target.checked)}
                  style={{ marginRight: "0.5em" }}
                />
                Add another
              </label>
            </div>
            <button
              type="button"
              className="btn btn-default"
              onClick={closeModal}
            >
              Close
            </button>
            <button
              type="button"
              className="btn btn-success"
              disabled={!selectedListens?.length}
              onClick={submitListens}
            >
              Submit {selectedListens.length ?? 0} listen
              {selectedListens.length > 1 ? "s" : ""}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
});
