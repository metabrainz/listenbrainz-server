import * as React from "react";
import { faHeart, faHeartBroken } from "@fortawesome/free-solid-svg-icons";
import { get } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import GlobalAppContext from "../utils/GlobalAppContext";
import {getRecordingMBID, getRecordingMSID} from "../utils/utils";

export type ListenFeedbackComponentProps = {
  newAlert: (
    type: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
  listen: BaseListenFormat;
  currentFeedback: ListenFeedBack;
  updateFeedbackCallback?: (
    recordingMsid: string,
    score: ListenFeedBack,
    recordingMbid?: string
  ) => void;
};

export default class ListenFeedbackComponent extends React.Component<
  ListenFeedbackComponentProps
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  submitFeedback = async (score: ListenFeedBack) => {
    const { listen, updateFeedbackCallback, newAlert } = this.props;
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
            updateFeedbackCallback(recordingMSID, score, recordingMBID);
          }
        }
      } catch (error) {
        newAlert(
          "danger",
          "Error while submitting feedback",
          error?.message ?? error.toString()
        );
      }
    }
  };

  render() {
    const { currentFeedback, listen } = this.props;
    const recordingMSID = getRecordingMSID(listen);
    if (!recordingMSID) {
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
