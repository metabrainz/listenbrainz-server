import { isUndefined } from "lodash";
import APIServiceClass from "./APIService";
// Gotta import this one with require instead of import…from
const throttleAsync = require("@jcoreio/async-throttle");

export default class RecordingFeedbackManager {
  mbidFetchQueue: string[] = [];
  msidFetchQueue: string[] = [];
  recordingMBIDFeedbackMap: Map<string, ListenFeedBack> = new Map();
  recordingMSIDFeedbackMap: Map<string, ListenFeedBack> = new Map();
  subscriptions: Map<
    string,
    Array<(newValue: ListenFeedBack) => void>
  > = new Map();

  DEBOUNCE_MS = 150;

  throttledFetchFeedback;
  APIService: APIServiceClass;
  currentUser?: ListenBrainzUser;

  constructor(APIService: APIServiceClass, currentUser?: ListenBrainzUser) {
    this.throttledFetchFeedback = throttleAsync(
      this.fetchFeedback,
      this.DEBOUNCE_MS
    );
    this.APIService = APIService;
    this.currentUser = currentUser;
  }

  subscribe = (ID: string, setFunction: (newValue: ListenFeedBack) => void) => {
    if (this.subscriptions.has(ID)) {
      const previousSubscriptions = this.subscriptions.get(ID) ?? [];
      this.subscriptions.set(ID, [...previousSubscriptions, setFunction]);
    } else {
      this.subscriptions.set(ID, [setFunction]);
    }
  };

  unsubscribe = (
    recordingID: string,
    setFunction: (newValue: ListenFeedBack) => void
  ) => {
    if (this.subscriptions.has(recordingID)) {
      const subscriptionsForRecording = this.subscriptions.get(recordingID);
      if (!subscriptionsForRecording || subscriptionsForRecording?.length < 2) {
        this.subscriptions.delete(recordingID);
      } else {
        this.subscriptions.set(
          recordingID,
          subscriptionsForRecording.filter(
            (savedSetFunc) => savedSetFunc !== setFunction
          )
        );
      }
    }
  };

  fetchFeedback = async () => {
    if (!this.currentUser?.name) {
      return;
    }
    const recordingMBIDs = [...this.mbidFetchQueue].filter(
      (string) => string?.length
    );
    const recordingMSIDs = [...this.msidFetchQueue].filter(
      (string) => string?.length
    );

    if (recordingMBIDs?.length || recordingMSIDs?.length) {
      const data = await this.APIService.getFeedbackForUserForRecordings(
        this.currentUser.name,
        recordingMBIDs,
        recordingMSIDs
      );
      data.feedback?.forEach((fb: FeedbackResponse) => {
        if (fb.recording_mbid) {
          this.recordingMBIDFeedbackMap.set(fb.recording_mbid, fb.score);
          this.updateSubscribed(fb.recording_mbid, fb.score);
        }
        if (fb.recording_msid) {
          this.recordingMSIDFeedbackMap.set(fb.recording_msid, fb.score);
          this.updateSubscribed(fb.recording_msid, fb.score);
        }
      });
      // empty the queues
      this.mbidFetchQueue.length = 0;
      this.msidFetchQueue.length = 0;
      // TODO: add retry mechanism ?
    }
  };

  getFeedback = async (
    MBID?: string,
    MSID?: string
  ): Promise<ListenFeedBack | undefined> => {
    if (!MBID && !MSID) {
      return undefined;
    }
    // If value is in feedback map, return early;
    if (MBID && this.recordingMBIDFeedbackMap.has(MBID)) {
      return this.recordingMBIDFeedbackMap.get(MBID);
    }
    if (MSID && this.recordingMSIDFeedbackMap.has(MSID)) {
      return this.recordingMSIDFeedbackMap.get(MSID);
    }
    if (MBID) {
      this.mbidFetchQueue.push(MBID);
    }
    if (MSID) {
      this.msidFetchQueue.push(MSID);
    }
    await this.throttledFetchFeedback();
    if (MBID) {
      const mbidFeedback = this.recordingMBIDFeedbackMap.get(MBID);
      if (!isUndefined(mbidFeedback)) {
        return mbidFeedback;
      }
    }
    if (MSID) {
      return this.recordingMSIDFeedbackMap.get(MSID);
    }
    return undefined;
  };

  submitFeedback = async (
    score: ListenFeedBack,
    recordingMBID?: string,
    recordingMSID?: string
  ) => {
    if (this.currentUser?.auth_token) {
      const status = await this.APIService.submitFeedback(
        this.currentUser.auth_token,
        score,
        recordingMSID,
        recordingMBID
      );
      if (status === 200) {
        if (recordingMBID) {
          this.recordingMBIDFeedbackMap.set(recordingMBID, score);
          this.updateSubscribed(recordingMBID, score);
        }
        if (recordingMSID) {
          this.recordingMSIDFeedbackMap.set(recordingMSID, score);
          this.updateSubscribed(recordingMSID, score);
        }
      }
    }
  };

  updateSubscribed(recordingId: string, score: ListenFeedBack) {
    const subscriptions =
      this.subscriptions.has(recordingId) &&
      this.subscriptions.get(recordingId);
    if (subscriptions && subscriptions.length) {
      subscriptions.forEach((setFunc) => {
        setFunc(score);
      });
    }
  }
}
