import * as React from "react";
import { faHeart, faHeartBroken } from "@fortawesome/free-solid-svg-icons";
import { get } from "lodash";
import ListenControl from "./ListenControl";

type ListenFeedbackComponentProps = {
  newAlert: (
    type: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
  listen: BaseListenFormat;
  currentFeedback: ListenFeedBack;
  updateFeedbackCallback?: (
    recordingMsid: string,
    score: ListenFeedBack
  ) => void;
};

type ListenFeedbackComponentState = {};

export default class ListenFeedbackComponent extends React.Component<
  ListenFeedbackComponentProps,
  ListenFeedbackComponentState
> {
  submitFeedback = async (score: ListenFeedBack) => {
    const { listen, updateFeedbackCallback, newAlert } = this.props;
    const { APIService, currentUser } = this.context;
    if (currentUser?.auth_token) {
      const recordingMSID = get(
        listen,
        "track_metadata.additional_info.recording_msid"
      );

      try {
        const status = await APIService.submitFeedback(
          currentUser.auth_token,
          recordingMSID,
          score
        );
        if (status === 200) {
          //   this.setState({ feedback: score });
          if (updateFeedbackCallback) {
            updateFeedbackCallback(recordingMSID, score);
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
    const recordingMSID = get(
      listen,
      "track_metadata.additional_info.recording_msid"
    );
    if (!recordingMSID) {
      return null;
    }
    return (
      <>
        <ListenControl
          icon={faHeart}
          title="Love"
          action={() => this.submitFeedback(currentFeedback === 1 ? 0 : 1)}
          className={`${currentFeedback === 1 ? " loved" : ""}`}
        />
        <ListenControl
          icon={faHeartBroken}
          title="Hate"
          action={() => this.submitFeedback(currentFeedback === -1 ? 0 : -1)}
          className={`${currentFeedback === -1 ? " hated" : ""}`}
        />
      </>
    );
  }
}
