import { isNaN } from "lodash";
import * as React from "react";

type ProgressBarProps = {
  progressMs: number;
  durationMs: number;
  seekToPositionMs: (msTimeCode: number) => void;
};

// How many milliseconds to navigate to with keyboard left/right arrows
const keyboardStepMS: number = 5000;
const keyboardBigStepMS: number = 10000;

const ProgressBar = (props: ProgressBarProps) => {
  const { durationMs, progressMs, seekToPositionMs } = props;
  const progressPercentage = Math.round(
    Number((progressMs * 100) / durationMs)
  );
  const hideProgressBar = isNaN(progressPercentage) || progressPercentage <= 0;

  const progressClickHandler = (
    event: React.MouseEvent<HTMLInputElement>
  ): void => {
    const progressBarBoundingRect = event.currentTarget.getBoundingClientRect();
    const progressBarWidth = progressBarBoundingRect.width;
    const musicPlayerXOffset = progressBarBoundingRect.x;
    const absoluteClickXPos = event.clientX;
    const relativeClickXPos = absoluteClickXPos - musicPlayerXOffset;
    const percentPos = relativeClickXPos / progressBarWidth;
    const positionMs = Math.round(durationMs * percentPos);
    seekToPositionMs(positionMs);
  };

  const onKeyPressHandler = (
    event: React.KeyboardEvent<HTMLInputElement>
  ): void => {
    if (
      document.activeElement?.localName === "input" ||
      document.activeElement?.localName === "textarea"
    ) {
      // If user has a text input/textarea in focus, ignore key navigation
      return;
    }
    if (event.key === "ArrowLeft") {
      let oneStepEarlier;
      if (event.shiftKey) {
        oneStepEarlier = progressMs - keyboardStepMS;
      } else {
        oneStepEarlier = progressMs - keyboardBigStepMS;
      }
      seekToPositionMs(oneStepEarlier > 0 ? oneStepEarlier : 0);
    }
    if (event.key === "ArrowRight") {
      let oneStepLater;
      if (event.shiftKey) {
        oneStepLater = progressMs + keyboardBigStepMS;
      } else {
        oneStepLater = progressMs + keyboardStepMS;
      }
      if (oneStepLater <= durationMs - 500) {
        seekToPositionMs(oneStepLater);
      }
    }
  };

  return (
    <div
      className={`progress${hideProgressBar ? " hidden" : ""}`}
      onClick={progressClickHandler}
      onKeyDown={onKeyPressHandler}
      aria-label="Audio Progress Control"
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={progressPercentage}
      tabIndex={0}
    >
      <div
        className="progress-bar"
        style={{
          width: `${progressPercentage}%`,
        }}
      />
    </div>
  );
};

export default ProgressBar;
