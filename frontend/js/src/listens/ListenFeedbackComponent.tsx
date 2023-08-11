import * as React from "react";

import { faHeart, faHeartCrack } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { getRecordingMBID, getRecordingMSID } from "../utils/utils";

import useFeedbackMap from "../hooks/useFeedbackMap";

export type ListenFeedbackComponentProps = {
  listen: BaseListenFormat;
};

export default function ListenFeedbackComponent(
  props: ListenFeedbackComponentProps
) {
  const { listen } = props;
  const recordingMBID = getRecordingMBID(listen);
  const recordingMSID = getRecordingMSID(listen);

  const { feedbackValue: currentFeedback, update } = useFeedbackMap(
    recordingMBID,
    recordingMSID
  );
  if (!recordingMSID && !recordingMBID) {
    return null;
  }
  return (
    <>
      <FontAwesomeIcon
        icon={faHeart}
        title="Love"
        onClick={() => update(currentFeedback === 1 ? 0 : 1)}
        className={`${currentFeedback === 1 ? " loved" : ""}`}
      />
      <FontAwesomeIcon
        icon={faHeartCrack}
        title="Hate"
        onClick={() => update(currentFeedback === -1 ? 0 : -1)}
        className={`${currentFeedback === -1 ? " hated" : ""}`}
      />
    </>
  );
}
