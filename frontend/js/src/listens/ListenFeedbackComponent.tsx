import * as React from "react";
import { faHeart, faHeartBroken } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { toast } from "react-toastify";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getRecordingMBID, getRecordingMSID } from "../utils/utils";
import { ToastMsg } from "../notifications/Notifications";

export type ListenFeedbackComponentProps = {
  listen: BaseListenFormat;
  currentFeedback: ListenFeedBack;
  updateFeedbackCallback?: (
    recordingMbid: string,
    score: ListenFeedBack,
    recordingMsid?: string
  ) => void;
};

export default class ListenFeedbackComponent extends React.Component<
  ListenFeedbackComponentProps
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  submitFeedback = async (score: ListenFeedBack) => {
    const { listen, updateFeedbackCallback } = this.props;
    const { APIService, currentUser } = this.context;
    if (currentUser?.auth_token) {
      const recordingMSID = getRecordingMSID(listen);
      const recordingMBID = getRecordingMBID(listen);

      try {
        const status = await APIService.submitFeedback(
          currentUser.auth_token,
          score,
          recordingMSID,
          recordingMBID
        );
        if (status === 200) {
          if (updateFeedbackCallback) {
            updateFeedbackCallback(recordingMBID ?? "", score, recordingMSID);
          }
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

  render() {
    const { currentFeedback, listen } = this.props;
    const recordingMSID = getRecordingMSID(listen);
    const recordingMBID = getRecordingMBID(listen);
    if (!recordingMSID && !recordingMBID) {
      return null;
    }
    return (
      <>
        <FontAwesomeIcon
          icon={faHeart}
          title="Love"
          onClick={() => this.submitFeedback(currentFeedback === 1 ? 0 : 1)}
          className={`${currentFeedback === 1 ? " loved" : ""}`}
        />
        <FontAwesomeIcon
          icon={faHeartBroken}
          title="Hate"
          onClick={() => this.submitFeedback(currentFeedback === -1 ? 0 : -1)}
          className={`${currentFeedback === -1 ? " hated" : ""}`}
        />
      </>
    );
  }
}
