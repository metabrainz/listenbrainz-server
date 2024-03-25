import { isNaN, throttle } from "lodash";
import * as React from "react";
import ReactTooltip from "react-tooltip";
import { millisecondsToStr } from "../../playlists/utils";

type ProgressBarProps = {
  progressMs: number;
  durationMs: number;
  seekToPositionMs: (msTimeCode: number) => void;
};

// How many milliseconds to navigate to with keyboard left/right arrows
const KEYBOARD_STEP_MS: number = 5000;
const KEYBOARD_BIG_STEP_MS: number = 10000;

const EVENT_KEY_ARROWLEFT: string = "ArrowLeft";
const EVENT_KEY_ARROWRIGHT: string = "ArrowRight";
const EVENT_TYPE_CLICK: string = "click";
const EVENT_TYPE_MOUSEMOVE: string = "mousemove";
const MOUSE_THROTTLE_DELAY: number = 300;

const TOOLTIP_INITIAL_CONTENT: string = "0:00";
const TOOLTIP_TOP_OFFSET: number = 102;

function ProgressBar(props: ProgressBarProps) {
  const { durationMs, progressMs, seekToPositionMs } = props;
  const [tipContent, setTipContent] = React.useState(TOOLTIP_INITIAL_CONTENT);
  const progressPercentage = Number(
    ((progressMs * 100) / durationMs).toFixed(2)
  );
  const hideProgressBar = isNaN(progressPercentage) || progressPercentage <= 0;

  // Originally by ford04 - https://stackoverflow.com/a/62017005
  const useThrottle = (callback: any, delay: number | undefined) => {
    const options = { leading: true, trailing: false };
    const callbackRef = React.useRef(callback);
    React.useEffect(() => {
      callbackRef.current = callback;
    });
    return React.useCallback(
      throttle((...args: any) => callbackRef.current(...args), delay, options),
      [delay]
    );
  };

  const mouseEventHandler = useThrottle(
    (event: React.MouseEvent<HTMLInputElement>): void => {
      const progressBarBoundingRect = event.currentTarget.getBoundingClientRect();
      const progressBarWidth = progressBarBoundingRect.width;
      const musicPlayerXOffset = progressBarBoundingRect.x;
      const absoluteClickXPos = event.clientX;
      const relativeClickXPos = absoluteClickXPos - musicPlayerXOffset;
      const percentPos = relativeClickXPos / progressBarWidth;
      const positionMs = Math.round(durationMs * percentPos);
      const positionTime = millisecondsToStr(positionMs);

      if (event.type === EVENT_TYPE_MOUSEMOVE) {
        setTipContent(positionTime);
      } else if (event.type === EVENT_TYPE_CLICK) {
        seekToPositionMs(positionMs);
      }
    },
    MOUSE_THROTTLE_DELAY
  );

  const onKeyPressHandler = (
    event: React.KeyboardEvent<HTMLInputElement>
  ): void => {
    const activeElement = document.activeElement?.localName;
    if (activeElement === "input" || activeElement === "textarea") {
      // If user has a text input/textarea in focus, ignore key navigation
      return;
    }
    if (event.key === EVENT_KEY_ARROWLEFT) {
      let oneStepEarlier;
      if (event.shiftKey) {
        oneStepEarlier = progressMs - KEYBOARD_STEP_MS;
      } else {
        oneStepEarlier = progressMs - KEYBOARD_BIG_STEP_MS;
      }
      seekToPositionMs(oneStepEarlier > 0 ? oneStepEarlier : 0);
    }
    if (event.key === EVENT_KEY_ARROWRIGHT) {
      let oneStepLater;
      if (event.shiftKey) {
        oneStepLater = progressMs + KEYBOARD_BIG_STEP_MS;
      } else {
        oneStepLater = progressMs + KEYBOARD_STEP_MS;
      }
      if (oneStepLater <= durationMs - 500) {
        seekToPositionMs(oneStepLater);
      }
    }
  };

  return (
    <div
      className={`progress${hideProgressBar ? " hidden" : ""}`}
      onClick={mouseEventHandler}
      onMouseMove={mouseEventHandler}
      onKeyDown={onKeyPressHandler}
      aria-label="Audio progress control"
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={progressPercentage}
      tabIndex={0}
      data-tip={tipContent}
    >
      <div
        className="progress-bar"
        style={{
          width: `${progressPercentage}%`,
        }}
      />
      <ReactTooltip
        className="progress-tooltip"
        getContent={() => tipContent}
        globalEventOff="click"
        overridePosition={({ left, top }) => {
          // eslint-disable-next-line no-param-reassign
          top = document.documentElement.clientHeight - TOOLTIP_TOP_OFFSET;
          return { left, top };
        }}
      />
    </div>
  );
}

export default ProgressBar;
