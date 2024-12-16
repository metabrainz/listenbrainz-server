import * as React from "react";

import { faHeart, faHeartCrack } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { getRecordingMBID, getRecordingMSID } from "../../utils/utils";

import useFeedbackMap from "../../hooks/useFeedbackMap";
import ListenControl from "./ListenControl";

export type ListenFeedbackComponentProps = {
  listen: BaseListenFormat;
  type: "button" | "dropdown";
};

export default function ListenFeedbackComponent(
  props: ListenFeedbackComponentProps
) {
  const { listen, type } = props;
  const recordingMBID = getRecordingMBID(listen);
  const recordingMSID = getRecordingMSID(listen);

  const { feedbackValue: currentFeedback, update } = useFeedbackMap(
    recordingMBID,
    recordingMSID
  );
  if (!recordingMSID && !recordingMBID) {
    return null;
  }

  if (type === "dropdown") {
    return (
      <>
        <ListenControl
          buttonClassName={`btn btn-transparent love${
            currentFeedback === 1 ? " loved" : ""
          }`}
          text="Love"
          icon={faHeart}
          title="Love"
          action={() => update(currentFeedback === 1 ? 0 : 1)}
        />
        <ListenControl
          buttonClassName={`btn btn-transparent hate${
            currentFeedback === -1 ? " hated" : ""
          }`}
          text="Hate"
          icon={faHeartCrack}
          title="Hate"
          action={() => update(currentFeedback === -1 ? 0 : -1)}
        />
      </>
    );
  }

  return (
    <>
      <button
        title="Love"
        onClick={() => update(currentFeedback === 1 ? 0 : 1)}
        className={`btn btn-transparent love${
          currentFeedback === 1 ? " loved" : ""
        }`}
        type="button"
      >
        <FontAwesomeIcon icon={faHeart} fixedWidth />
      </button>
      <button
        title="Hate"
        onClick={() => update(currentFeedback === -1 ? 0 : -1)}
        className={`btn btn-transparent hate${
          currentFeedback === -1 ? " hated" : ""
        }`}
        type="button"
      >
        <FontAwesomeIcon icon={faHeartCrack} fixedWidth />
      </button>
    </>
  );
}
