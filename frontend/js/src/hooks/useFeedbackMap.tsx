import React, { useContext, useEffect, useState } from "react";
import { isUndefined } from "lodash";
import GlobalAppContext from "../utils/GlobalAppContext";

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
      .catch(console.error);
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
      await submitFeedback(newFeedbackValue, recordingMBID, recordingMSID);
    },
  };

  return feedbackMap;
}
