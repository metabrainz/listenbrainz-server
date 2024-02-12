import React, { useCallback, useContext, useState } from "react";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import DateTimePicker from "react-datetime-picker/dist/entry.nostyle";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCalendar } from "@fortawesome/free-regular-svg-icons";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { has } from "lodash";
import { toast } from "react-toastify";
import ListenControl from "../../common/listens/ListenControl";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { convertDateToUnixTimestamp } from "../../utils/utils";
import ListenCard from "../../common/listens/ListenCard";
import SearchTrackOrMBID from "../../utils/SearchTrackOrMBID";
import { ToastMsg } from "../../notifications/Notifications";

enum SubmitListenType {
  "track",
  "album",
}

function getListenFromTrack(
  selectedDate: Date,
  selectedTrackMetadata?: TrackMetadata
): Listen | undefined {
  if (!selectedTrackMetadata) {
    return undefined;
  }

  return {
    listened_at: convertDateToUnixTimestamp(selectedDate),
    track_metadata: {
      ...selectedTrackMetadata,
      additional_info: {
        ...selectedTrackMetadata.additional_info,
        submission_client: "listenbrainz web",
      },
    },
  };
}

export default NiceModal.create(() => {
  const modal = useModal();
  const { APIService, currentUser } = useContext(GlobalAppContext);
  const { auth_token } = currentUser;
  const [listenOption, setListenOption] = useState<SubmitListenType>(
    SubmitListenType.track
  );
  const [selectedTrack, setSelectedTrack] = useState<TrackMetadata>();
  const [customTimestamp, setCustomTimestamp] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date());

  const closeModal = useCallback(() => {
    modal.hide();
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

  const resetTrackSelection = () => {
    setSelectedTrack(undefined);
    setListenOption(SubmitListenType.track);
  };

  const submitListen = useCallback(async () => {
    if (auth_token) {
      if (selectedTrack) {
        const payload = getListenFromTrack(selectedDate, selectedTrack)!;

        try {
          const response = await APIService.submitListens(
            auth_token,
            "single",
            [payload]
          );
          await APIService.checkStatus(response);
          toast.success(
            <ToastMsg
              title="You added the Listen"
              message={`${selectedTrack.track_name} - ${selectedTrack.artist_name}`}
            />,
            { toastId: "added-listen-success" }
          );
          closeModal();
        } catch (error) {
          handleError(error, "Error while adding a listen");
        }
      }
    } else {
      toast.error(
        <ToastMsg
          title="You need to be logged in to Add a Listen"
          message={<a href="/login">Log in here</a>}
        />,
        { toastId: "auth-error" }
      );
    }
  }, [
    APIService,
    closeModal,
    auth_token,
    handleError,
    selectedDate,
    selectedTrack,
  ]);

  const listenFromSelectedTrack = getListenFromTrack(
    selectedDate,
    selectedTrack
  );

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
                onClick={resetTrackSelection}
              >
                Add track
              </button>
            </div>
            {listenOption === SubmitListenType.track && (
              <div>
                <SearchTrackOrMBID
                  onSelectRecording={(newSelectedTrackMetadata) => {
                    setSelectedTrack(newSelectedTrackMetadata);
                  }}
                />
                <div className="track-info">
                  <div>
                    {listenFromSelectedTrack && (
                      <ListenCard
                        listen={listenFromSelectedTrack}
                        showTimestamp={false}
                        showUsername={false}
                        // eslint-disable-next-line react/jsx-no-useless-fragment
                        feedbackComponent={<></>}
                        compact
                        additionalActions={
                          <ListenControl
                            buttonClassName="btn-transparent"
                            text=""
                            title="Reset"
                            icon={faTimesCircle}
                            iconSize="lg"
                            action={resetTrackSelection}
                          />
                        }
                      />
                    )}
                  </div>
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
              Close
            </button>
            <button
              type="submit"
              className="btn btn-success"
              data-dismiss="modal"
              disabled={!selectedTrack}
              onClick={submitListen}
            >
              Add Listen
            </button>
          </div>
        </form>
      </div>
    </div>
  );
});
