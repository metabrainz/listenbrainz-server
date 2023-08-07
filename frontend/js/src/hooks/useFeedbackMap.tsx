import React, { useContext, useEffect, useState } from "react";
import { toast } from "react-toastify";
import { isUndefined } from "lodash";
import { ToastMsg } from "../notifications/Notifications";
import GlobalAppContext from "../utils/GlobalAppContext";
import APIServiceClass from "../utils/APIService";

const throttleAsync = require("@jcoreio/async-throttle");

const recordingMBIDFeedbackMap = new Map<string, ListenFeedBack>();
const recordingMSIDFeedbackMap = new Map<string, ListenFeedBack>();

let mbidQueue: string[] = [];
const msidQueue: string[] = [];
let userName = "";
let savedAPIService: APIServiceClass;
const DEBOUNCE_MS = 150;

async function fetchFeedback() {
  if (!userName) {
    throw new SyntaxError("Username missing");
  }
  const recordingMBIDs = [...mbidQueue].filter((string) => string?.length);
  const recordingMSIDs = [...msidQueue].filter((string) => string?.length);

  if (recordingMBIDs?.length || recordingMSIDs?.length) {
    try {
      const data = await savedAPIService.getFeedbackForUserForRecordings(
        userName,
        recordingMBIDs,
        recordingMSIDs
      );
      data.feedback?.forEach((fb: FeedbackResponse) => {
        if (fb.recording_mbid) {
          recordingMBIDFeedbackMap.set(fb.recording_mbid, fb.score);
        }
        if (fb.recording_msid) {
          recordingMSIDFeedbackMap.set(fb.recording_msid, fb.score);
        }
      });
      // empty the queue
      mbidQueue = [];
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
    async write(
      MBID?: string,
      MSID?: string
    ): Promise<ListenFeedBack | undefined> {
      if (MBID) {
        mbidQueue.push(MBID);
      }
      if (MSID) {
        msidQueue.push(MSID);
      }
      try {
        await throttledFetchFeedback();
      } catch (error) {
        console.error(error);
      }
      if (MBID) {
        const mbidFeedback = recordingMBIDFeedbackMap.get(MBID);
        if (!isUndefined(mbidFeedback)) {
          return mbidFeedback;
        }
      }
      if (MSID) {
        return recordingMSIDFeedbackMap.get(MSID);
      }
      return undefined;
    },
  };
};

export default function useFeedbackMap(
  recordingMBID?: string,
  recordingMSID?: string
) {
  const { APIService, currentUser } = useContext(GlobalAppContext);
  const [feedbackValue, setFeedbackValue] = useState<ListenFeedBack>(0);
  userName = currentUser?.name;
  savedAPIService = APIService;

  useEffect(() => {
    const feedbackFetchQueue = createFetchQueue();
    // on load, add this MBID to the list and fetch feedback (throttled)
    feedbackFetchQueue
      .write(recordingMBID, recordingMSID)
      .catch(console.error)
      .finally(() => {
        if (recordingMBID) {
          const mbidFeedback = recordingMBIDFeedbackMap.get(recordingMBID);
          if (!isUndefined(mbidFeedback)) {
            setFeedbackValue(mbidFeedback);
          }
        } else if (recordingMSID) {
          const msidFeedback = recordingMSIDFeedbackMap.get(recordingMSID);
          if (!isUndefined(msidFeedback)) {
            setFeedbackValue(msidFeedback);
          }
        }
      });
  }, [recordingMBID, recordingMSID]);

  const submitFeedback = async (score: ListenFeedBack) => {
    if (currentUser?.auth_token) {
      try {
        const status = await APIService.submitFeedback(
          currentUser.auth_token,
          score,
          recordingMSID,
          recordingMBID
        );
        if (status === 200) {
          if (recordingMBID) {
            recordingMBIDFeedbackMap.set(recordingMBID, score);
          }
          if (recordingMSID) {
            recordingMSIDFeedbackMap.set(recordingMSID, score);
          }
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
