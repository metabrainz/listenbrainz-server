import { throttle } from "lodash";
import * as React from "react";
import { Overlay, Tooltip } from "react-bootstrap";
import type { OverlayInjectedProps } from "react-bootstrap/Overlay";
import { useAtomValue } from "jotai";
import { millisecondsToStr } from "../../playlists/utils";
import { durationMsAtom, progressMsAtom } from "./BrainzPlayerAtoms";

type ProgressBarProps = {
  seekToPositionMs: (msTimeCode: number) => void;
  showNumbers?: boolean;
};

// How many milliseconds to navigate to with keyboard left/right arrows
const KEYBOARD_STEP_MS: number = 5000;
const KEYBOARD_BIG_STEP_MS: number = 10000;

const EVENT_KEY_ARROWLEFT: string = "ArrowLeft";
const EVENT_KEY_ARROWRIGHT: string = "ArrowRight";
const MOUSE_THROTTLE_DELAY: number = 300;

const TOOLTIP_INITIAL_CONTENT: string = "0:00";

type ProgressTooltipProps = {
  overlayProps: OverlayInjectedProps;
  tipContent: string;
  tooltipXPosition: number;
};

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

function ProgressTooltip({
  overlayProps,
  tipContent,
  tooltipXPosition,
}: ProgressTooltipProps) {
  React.useEffect(() => {
    overlayProps.popper?.scheduleUpdate?.();
  }, [overlayProps.popper, tooltipXPosition]);

  return (
    <Tooltip
      id="progress-tooltip"
      {...overlayProps}
      className={`progress-tooltip ${overlayProps.className ?? ""}`.trim()}
    >
      {tipContent}
    </Tooltip>
  );
}

function ProgressBar(props: ProgressBarProps) {
  const progressMs = useAtomValue(progressMsAtom);
  const durationMs = useAtomValue(durationMsAtom);

  const { seekToPositionMs, showNumbers } = props;
  const [tipContent, setTipContent] = React.useState(TOOLTIP_INITIAL_CONTENT);
  const [showTooltip, setShowTooltip] = React.useState(false);
  const [tooltipXPosition, setTooltipXPosition] = React.useState(0);
  const progressBarRef = React.useRef<HTMLDivElement>(null);
  const tooltipTargetRef = React.useRef<HTMLSpanElement>(null);
  const isScrubbingRef = React.useRef(false);
  const ignoreNextClickRef = React.useRef(false);
  const progressPercentage = Number(
    ((progressMs * 100) / durationMs).toFixed()
  );
  const throttledSetTipContent = useThrottle((positionTime: string): void => {
    setTipContent(positionTime);
  }, MOUSE_THROTTLE_DELAY);
  const throttledSeekToPositionMs = useThrottle((positionMs: number): void => {
    seekToPositionMs(positionMs);
  }, MOUSE_THROTTLE_DELAY);

  const getPositionFromClientX = (clientX: number) => {
    const progressBarBoundingRect = progressBarRef.current?.getBoundingClientRect();
    if (!progressBarBoundingRect) {
      return null;
    }
    const progressBarWidth = progressBarBoundingRect.width;
    if (!progressBarWidth) {
      return null;
    }
    const musicPlayerXOffset = progressBarBoundingRect.x;
    const relativeClickXPos = clientX - musicPlayerXOffset;
    const percentPos = Math.max(
      0,
      Math.min(1, relativeClickXPos / progressBarWidth)
    );
    const positionMs = Math.round(durationMs * percentPos);

    return {
      positionMs,
      positionTime: millisecondsToStr(positionMs),
      tooltipXPosition: clientX,
    };
  };

  const updateTooltipFromClientX = (
    clientX: number,
    updateContentImmediately = false
  ) => {
    const mousePosition = getPositionFromClientX(clientX);
    if (!mousePosition) {
      return null;
    }

    if (updateContentImmediately) {
      setTipContent(mousePosition.positionTime);
    } else {
      throttledSetTipContent(mousePosition.positionTime);
    }
    setTooltipXPosition(mousePosition.tooltipXPosition);
    setShowTooltip(true);
    return mousePosition.positionMs;
  };

  const onMouseMoveHandler = (
    event: React.MouseEvent<HTMLDivElement>
  ): void => {
    if (/Mobi/.test(navigator.userAgent)) {
      setShowTooltip(false);
      return;
    }

    updateTooltipFromClientX(event.clientX);
  };

  const onClickHandler = (event: React.MouseEvent<HTMLDivElement>): void => {
    if (ignoreNextClickRef.current) {
      ignoreNextClickRef.current = false;
      return;
    }

    const positionMs = updateTooltipFromClientX(event.clientX, true);
    if (positionMs === null) {
      return;
    }
    setShowTooltip(false);
    seekToPositionMs(positionMs);
  };

  const onPointerDownHandler = (
    event: React.PointerEvent<HTMLDivElement>
  ): void => {
    if (event.pointerType === "mouse") {
      return;
    }

    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    isScrubbingRef.current = true;
    ignoreNextClickRef.current = true;

    const positionMs = updateTooltipFromClientX(event.clientX, true);
    if (positionMs !== null) {
      seekToPositionMs(positionMs);
    }
  };

  const onPointerMoveHandler = (
    event: React.PointerEvent<HTMLDivElement>
  ): void => {
    if (event.pointerType === "mouse" || !isScrubbingRef.current) {
      return;
    }

    event.preventDefault();
    const positionMs = updateTooltipFromClientX(event.clientX);
    if (positionMs !== null) {
      throttledSeekToPositionMs(positionMs);
    }
  };

  const stopScrubbing = (event: React.PointerEvent<HTMLDivElement>): void => {
    if (event.pointerType === "mouse" || !isScrubbingRef.current) {
      return;
    }

    event.preventDefault();
    const positionMs = updateTooltipFromClientX(event.clientX, true);
    if (positionMs !== null) {
      seekToPositionMs(positionMs);
    }

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    isScrubbingRef.current = false;
    setShowTooltip(false);
  };

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
        onClick={onClickHandler}
        onMouseMove={onMouseMoveHandler}
        onMouseLeave={() => setShowTooltip(false)}
        onPointerDown={onPointerDownHandler}
        onPointerMove={onPointerMoveHandler}
        onPointerUp={stopScrubbing}
        onPointerCancel={stopScrubbing}
        onKeyDown={onKeyPressHandler}
        aria-label="Audio progress control"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progressPercentage || 0}
        tabIndex={0}
        ref={progressBarRef}
      >
        <div className="progress-bar bg-info" style={progressBarStyle} />
        <span
          ref={tooltipTargetRef}
          style={{
            position: "fixed",
            left: tooltipXPosition,
            top: progressBarRef.current?.getBoundingClientRect().top,
            width: 1,
            height: 1,
            pointerEvents: "none",
          }}
        />
        <Overlay
          target={tooltipTargetRef.current}
          show={showTooltip}
          placement="top"
          transition={false}
        >
          {(overlayProps) => (
            <ProgressTooltip
              overlayProps={overlayProps}
              tipContent={tipContent}
              tooltipXPosition={tooltipXPosition}
            />
          )}
        </Overlay>
      </div>
      {showNumbers && (
        <div className="progress-numbers">
          <span>{millisecondsToStr(progressMs)}</span>
          <span className="divider">&#8239;/&#8239;</span>
          <span>{millisecondsToStr(durationMs)}</span>
        </div>
      )}
    </div>
  );
}

export default ProgressBar;
