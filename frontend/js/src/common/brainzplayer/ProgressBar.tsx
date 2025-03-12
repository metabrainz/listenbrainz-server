import { throttle } from "lodash";
import * as React from "react";
import ReactTooltip from "react-tooltip";
import { millisecondsToStr } from "../../playlists/utils";
import { useBrainzPlayerContext } from "./BrainzPlayerContext";

type ProgressBarProps = {
  seekToPositionMs: (msTimeCode: number) => void;
  showNumbers?: boolean;
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
const TOOLTIP_TOP_OFFSET: number = 39;

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

function ProgressBar(props: ProgressBarProps) {
  const brainzPlayerContext = useBrainzPlayerContext();
  const brainzPlayerContextRef = React.useRef(brainzPlayerContext);
  brainzPlayerContextRef.current = brainzPlayerContext;

  const { seekToPositionMs, showNumbers } = props;
  const [tipContent, setTipContent] = React.useState(TOOLTIP_INITIAL_CONTENT);
  const progressBarRef = React.useRef<HTMLDivElement>(null);
  const progressPercentage = Number(
    (
      (brainzPlayerContextRef.current.progressMs * 100) /
      brainzPlayerContextRef.current.durationMs
    ).toFixed()
  );

  const mouseEventHandler = useThrottle(
    (event: React.MouseEvent<HTMLInputElement>): void => {
      const progressBarBoundingRect = event.currentTarget.getBoundingClientRect();
      const progressBarWidth = progressBarBoundingRect.width;
      const musicPlayerXOffset = progressBarBoundingRect.x;
      const absoluteClickXPos = event.clientX;
      const relativeClickXPos = absoluteClickXPos - musicPlayerXOffset;
      const percentPos = relativeClickXPos / progressBarWidth;
      const positionMs = Math.round(
        brainzPlayerContextRef.current.durationMs * percentPos
      );
      const positionTime = millisecondsToStr(positionMs);

      const isMobile = /Mobi/.test(navigator.userAgent);

      if (isMobile) {
        setTipContent(positionTime);
        seekToPositionMs(positionMs);
        return;
      }

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
        oneStepEarlier =
          brainzPlayerContextRef.current.progressMs - KEYBOARD_STEP_MS;
      } else {
        oneStepEarlier =
          brainzPlayerContextRef.current.progressMs - KEYBOARD_BIG_STEP_MS;
      }
      seekToPositionMs(oneStepEarlier > 0 ? oneStepEarlier : 0);
    }
    if (event.key === EVENT_KEY_ARROWRIGHT) {
      let oneStepLater;
      if (event.shiftKey) {
        oneStepLater =
          brainzPlayerContextRef.current.progressMs + KEYBOARD_BIG_STEP_MS;
      } else {
        oneStepLater =
          brainzPlayerContextRef.current.progressMs + KEYBOARD_STEP_MS;
      }
      if (oneStepLater <= brainzPlayerContextRef.current.durationMs - 500) {
        seekToPositionMs(oneStepLater);
      }
    }
  };

  const progressBarStyle: React.CSSProperties = {
    width: `${progressPercentage || 0}%`,
  };
  if (!progressPercentage || progressPercentage === 0) {
    // Hide little nubbin' appearing when at 0, for those with mild OCD.
    progressBarStyle.borderRight = "none";
  }

  return (
    <div className="progress-bar-wrapper">
      <div
        className="progress"
        onClick={mouseEventHandler}
        onMouseMove={mouseEventHandler}
        onKeyDown={onKeyPressHandler}
        aria-label="Audio progress control"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progressPercentage || 0}
        tabIndex={0}
        data-tip={tipContent}
        ref={progressBarRef}
      >
        <div className="progress-bar" style={progressBarStyle} />
        <ReactTooltip
          className="progress-tooltip"
          getContent={() => tipContent}
          globalEventOff="click"
          overridePosition={({ left, top }) => {
            const progressBarBoundingRect = progressBarRef.current?.getBoundingClientRect();
            if (progressBarBoundingRect) {
              // eslint-disable-next-line no-param-reassign
              top = progressBarBoundingRect.top - TOOLTIP_TOP_OFFSET;
            }
            return { left, top };
          }}
        />
      </div>
      {showNumbers && (
        <div className="progress-numbers">
          <span>
            {millisecondsToStr(brainzPlayerContextRef.current.progressMs)}
          </span>
          <span className="divider">&#8239;/&#8239;</span>
          <span>
            {millisecondsToStr(brainzPlayerContextRef.current.durationMs)}
          </span>
        </div>
      )}
    </div>
  );
}

export default ProgressBar;
