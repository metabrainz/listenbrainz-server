import React, { useCallback, useContext, useState } from "react";
import DateTimePicker from "react-datetime-picker/dist/entry.nostyle";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCalendar } from "@fortawesome/free-regular-svg-icons";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import { Link } from "react-router-dom";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { convertDateToUnixTimestamp } from "../../utils/utils";
import { ToastMsg } from "../../notifications/Notifications";
import AddSingleListen from "./AddSingleListen";
import AddAlbumListens from "./AddAlbumListens";

enum SubmitListenType {
  "track",
  "album",
}

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

  const getListenFromTrack = useCallback(
    (track: MusicBrainzTrack & WithArtistCredits): Listen => {
      return {
        listened_at: convertDateToUnixTimestamp(selectedDate),
        track_metadata: {
          track_name: track.title,
          artist_name:
            track["artist-credit"]
              ?.map((artist) => `${artist.name}${artist.joinphrase}`)
              .join("") ?? "",
          additional_info: {
            recording_mbid: track.recording.id,
            // ...track.additional_info,
            submission_client: "listenbrainz web",
          },
        },
      };
    },
    [selectedDate]
  );

  const setSelectedAlbumTracks = useCallback(
    (selectedTracks: Array<MusicBrainzTrack & WithArtistCredits>) => {
      setSelectedListens(selectedTracks.map(getListenFromTrack));
    },
    [setSelectedListens]
  );

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

  const submitListen = useCallback(async () => {
    if (auth_token) {
      if (selectedListens) {
        try {
          const response = await APIService.submitListens(
            auth_token,
            "single",
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
  }, [APIService, closeModal, auth_token, handleError, selectedListens]);

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
              <AddAlbumListens onPayloadChange={setSelectedAlbumTracks} />
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
              disabled={!selectedListens?.length}
              onClick={submitListen}
            >
              Add {selectedListens.length} listen
              {selectedListens.length > 1 ? "s" : ""}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
});
