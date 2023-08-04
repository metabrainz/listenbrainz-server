import React, { useContext, useEffect, useState } from "react";
import { toast } from "react-toastify";
import { isUndefined } from "lodash";
import throttleAsync from "@jcoreio/async-throttle";
import { ToastMsg } from "../notifications/Notifications";
import GlobalAppContext from "../utils/GlobalAppContext";
import APIServiceClass from "../utils/APIService";

const recordingFeedbackMap = new Map<string, ListenFeedBack>();

let queueSingleton: string[] = [];
let userName = "";
let savedAPIService: APIServiceClass;
const DEBOUNCE_MS = 150;

async function fetchFeedback() {
  if (!userName) {
    throw new SyntaxError("Username missing");
  }
  const recordingMBIDs = [...queueSingleton].filter((string) => string?.length);

  if (recordingMBIDs?.length) {
    try {
      const data = await savedAPIService.getFeedbackForUserForRecordings(
        userName,
        recordingMBIDs
      );
      data.feedback?.forEach((fb: FeedbackResponse) => {
        if (fb.recording_mbid) {
          recordingFeedbackMap.set(fb.recording_mbid, fb.score);
        }
      });
      // empty the queue
      queueSingleton = [];
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error fetching love/hate feedback"
          message={typeof error === "object" ? error.message : error}
        />,
        { toastId: "feedback-error" }
      );
      // TODO: add retry mechanism ?
    }
  }
}

const throttledFetchFeedback = throttleAsync(fetchFeedback, DEBOUNCE_MS);

const createFetchQueue = () => {
  return {
    async write(MBID: string): Promise<ListenFeedBack | undefined> {
      queueSingleton.push(MBID);
      try {
        await throttledFetchFeedback();
      } catch (error) {
        console.error(error);
      }
      return recordingFeedbackMap.get(MBID);
    },
  };
};

export default function useFeedbackMap(recordingMBID: string) {
  const { APIService, currentUser } = useContext(GlobalAppContext);
  const [feedbackValue, setFeedbackValue] = useState<ListenFeedBack>(0);
  userName = currentUser?.name;
  savedAPIService = APIService;

  useEffect(() => {
    const feedbackFetchQueue = createFetchQueue();
    // on load, add this MBID to the list and fetch feedback (throttled)
    feedbackFetchQueue
      .write(recordingMBID)
      .catch(console.error)
      .finally(() => {
        const feedback = recordingFeedbackMap.get(recordingMBID);
        if (!isUndefined(feedback)) {
          setFeedbackValue(feedback);
        }
      });
  }, [recordingMBID]);

  const submitFeedback = async (score: ListenFeedBack) => {
    if (currentUser?.auth_token) {
      // const recordingMSID = getRecordingMSID(listen);

      try {
        const status = await APIService.submitFeedback(
          currentUser.auth_token,
          score,
          undefined,
          recordingMBID
        );
        if (status === 200) {
          recordingFeedbackMap.set(recordingMBID, score);
          setFeedbackValue(score);
        }
      } catch (error) {
        toast.error(
          <ToastMsg
            title=" Error while submitting feedback"
            message={error?.message ?? error.toString()}
          />,
          { toastId: "submit-feedback-error" }
        );
      }
    }
  };

  const feedbackMap = {
    value: feedbackValue,
    update: async (newFeedbackValue: ListenFeedBack) => {
      await submitFeedback(newFeedbackValue);
    },
  };

  return feedbackMap;
}
