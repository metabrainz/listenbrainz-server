import React, { useContext, useEffect, useState } from "react";
import { isUndefined } from "lodash";
import { toast } from "react-toastify";
import GlobalAppContext from "../utils/GlobalAppContext";
import { ToastMsg } from "../notifications/Notifications";

export default function useFeedbackMap(
  recordingMBID?: string,
  recordingMSID?: string
) {
  const { recordingFeedbackManager } = useContext(GlobalAppContext);

  const {
    recordingMBIDFeedbackMap,
    recordingMSIDFeedbackMap,
    getFeedback,
    submitFeedback,
    subscribe,
    unsubscribe,
  } = recordingFeedbackManager;

  const [feedbackValue, setFeedbackValue] = useState<ListenFeedBack>(
    recordingMBIDFeedbackMap.get(recordingMBID!) ??
      recordingMSIDFeedbackMap.get(recordingMSID!) ??
      0
  );

  useEffect(() => {
    // on load, add this MBID to the list and fetch feedback (throttled)
    getFeedback(recordingMBID, recordingMSID)
      .then((value) => {
        if (!isUndefined(value)) {
          setFeedbackValue(value);
        }
      })
      .catch((error) => {
        toast.error(
          <ToastMsg
            title="Error fetching love/hate feedback"
            message={typeof error === "object" ? error.message : error}
          />,
          { toastId: "feedback-error" }
        );
      });
    if (recordingMBID) {
      subscribe(recordingMBID, setFeedbackValue);
    } else if (recordingMSID) {
      subscribe(recordingMSID, setFeedbackValue);
    }
    return () => {
      if (recordingMBID) {
        unsubscribe(recordingMBID, setFeedbackValue);
      } else if (recordingMSID) {
        unsubscribe(recordingMSID, setFeedbackValue);
      }
    };
  }, [
    getFeedback,
    recordingMBID,
    recordingMBIDFeedbackMap,
    recordingMSID,
    recordingMSIDFeedbackMap,
    subscribe,
    unsubscribe,
  ]);

  const feedbackMap = {
    feedbackValue,
    update: async (newFeedbackValue: ListenFeedBack) => {
      try {
        await submitFeedback(newFeedbackValue, recordingMBID, recordingMSID);
      } catch (error) {
        toast.error(
          <ToastMsg
            title=" Error while submitting feedback"
            message={error?.message ?? error.toString()}
          />,
          { toastId: "submit-feedback-error" }
        );
      }
    },
  };

  return feedbackMap;
}
