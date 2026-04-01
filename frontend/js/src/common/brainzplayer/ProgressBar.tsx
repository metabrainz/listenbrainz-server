import { throttle } from "lodash";
import * as React from "react";
import ReactTooltip from "react-tooltip";
import { useAtomValue } from "jotai";
import { millisecondsToStr } from "../../playlists/utils";
import {
  durationMsAtom,
  progressMsAtom,
  playerPausedAtom,
  updateTimeAtom,
} from "./BrainzPlayerAtoms";

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
const HANDLE_RADIUS = 5; // px — handle is 10×10px

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
  const progressMs = useAtomValue(progressMsAtom);
  const durationMs = useAtomValue(durationMsAtom);
  const playerPaused = useAtomValue(playerPausedAtom);
  const updateTime = useAtomValue(updateTimeAtom);

  const { seekToPositionMs, showNumbers } = props;
  const [tipContent, setTipContent] = React.useState(TOOLTIP_INITIAL_CONTENT);
  const progressBarRef = React.useRef<HTMLDivElement>(null);
  const progressBarInnerRef = React.useRef<HTMLDivElement>(null);
  const handleRef = React.useRef<HTMLDivElement>(null);
  const rafRef = React.useRef<number>(0);
  const isDraggingRef = React.useRef<boolean>(false);
  const rectCacheRef = React.useRef<DOMRect | null>(null);
  const pendingSeekMsRef = React.useRef<number>(-1);
  const seekVisualMsRef = React.useRef<number>(-1);

  React.useEffect(() => {
    const tick = () => {
      if (isDraggingRef.current) return;
      const base =
        pendingSeekMsRef.current >= 0 ? pendingSeekMsRef.current : progressMs;
      const elapsed = playerPaused ? 0 : performance.now() - updateTime;
      const liveProgressMs = base + elapsed;
      const ratio = Math.min(liveProgressMs / durationMs, 1) || 0;
      if (progressBarInnerRef.current) {
        progressBarInnerRef.current.style.transform = `scaleX(${ratio})`;
      }
      if (handleRef.current) {
        const barWidth =
          progressBarInnerRef.current?.parentElement?.getBoundingClientRect()
            .width ?? 0;
        const handleX = ratio * barWidth;
        handleRef.current.style.setProperty("--handle-x", `${handleX}px`);
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [progressMs, durationMs, playerPaused, updateTime]);

  const getMsFromClientX = (clientX: number): number => {
    const rect = rectCacheRef.current;
    if (!rect || durationMs <= 0) return 0;
    const ratio = Math.max(0, Math.min((clientX - rect.left) / rect.width, 1));
    return ratio * durationMs;
  };

  const flushVisuals = (msPosition: number): void => {
    setTipContent(millisecondsToStr(msPosition));
    const ratio = Math.min(msPosition / durationMs, 1) || 0;
    const barWidth = rectCacheRef.current?.width ?? 0;
    const handleX = ratio * barWidth;
    if (progressBarInnerRef.current) {
      progressBarInnerRef.current.style.transform = `scaleX(${ratio})`;
    }
    if (handleRef.current) {
      handleRef.current.style.setProperty("--handle-x", `${handleX}px`);
    }
  };

  React.useEffect(() => {
    const onPointerMove = (e: PointerEvent) => {
      if (!isDraggingRef.current) return;
      const msPos = getMsFromClientX(e.clientX);
      seekVisualMsRef.current = msPos;
      flushVisuals(msPos);
    };

    const onPointerUp = (e: PointerEvent) => {
      if (!isDraggingRef.current) return;
      isDraggingRef.current = false;
      document.body.style.cursor = "";
      const msPos = getMsFromClientX(e.clientX);
      pendingSeekMsRef.current = msPos;
      seekToPositionMs(msPos);
      document
        .querySelectorAll(".progress.dragging")
        .forEach((el) => el.classList.remove("dragging"));
    };

    document.addEventListener("pointermove", onPointerMove);
    document.addEventListener("pointerup", onPointerUp);
    return () => {
      document.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("pointerup", onPointerUp);
    };
  }, [seekToPositionMs, durationMs]);

  React.useEffect(() => {
    if (pendingSeekMsRef.current < 0) return;
    if (Math.abs(progressMs - pendingSeekMsRef.current) < 500) {
      pendingSeekMsRef.current = -1;
    }
  }, [progressMs]);

  React.useEffect(() => {
    const onResize = () => {
      if (isDraggingRef.current && progressBarRef.current) {
        rectCacheRef.current =
          progressBarRef.current.getBoundingClientRect();
      }
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

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
        oneStepEarlier = progressMs - KEYBOARD_STEP_MS;
      } else {
        oneStepEarlier = progressMs - KEYBOARD_BIG_STEP_MS;
      }
      const newPos = oneStepEarlier > 0 ? oneStepEarlier : 0;
      pendingSeekMsRef.current = newPos;
      seekToPositionMs(newPos);
    }
    if (event.key === EVENT_KEY_ARROWRIGHT) {
      let oneStepLater;
      if (event.shiftKey) {
        oneStepLater = progressMs + KEYBOARD_BIG_STEP_MS;
      } else {
        oneStepLater = progressMs + KEYBOARD_STEP_MS;
      }
      if (oneStepLater <= durationMs - 500) {
        pendingSeekMsRef.current = oneStepLater;
        seekToPositionMs(oneStepLater);
      }
    }
  };


  return (
    <div className="progress-bar-wrapper">
      <div
        className="progress"
        onClick={mouseEventHandler}
        onMouseMove={mouseEventHandler}
        onKeyDown={onKeyPressHandler}
        onMouseDown={(e: React.MouseEvent<HTMLDivElement>) => {
          e.preventDefault();
          isDraggingRef.current = true;
          document.body.style.cursor = "grabbing";
          rectCacheRef.current = (
            e.currentTarget as HTMLDivElement
          ).getBoundingClientRect();
          if (handleRef.current) {
            handleRef.current.style.transform =
              "translate(-50%, -50%) scaleX(1)";
          }
          (e.currentTarget as HTMLDivElement).classList.add("dragging");
          const msPos = getMsFromClientX(e.clientX);
          seekVisualMsRef.current = msPos;
          flushVisuals(msPos);
        }}
        onMouseEnter={() => {
          if (handleRef.current) {
            handleRef.current.style.transform =
              "translate(-50%, -50%) scaleX(1)";
          }
        }}
        onMouseLeave={() => {
          if (handleRef.current) {
            handleRef.current.style.transform =
              "translate(-50%, -50%) scaleX(0)";
          }
        }}
        aria-label="Audio progress control"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={0}
        tabIndex={0}
        data-tip={tipContent}
        ref={progressBarRef}
      >
        <div
          className="progress-bar bg-info"
          ref={progressBarInnerRef}
          style={{ transform: "scaleX(0)", transformOrigin: "left" }}
        />
        <div
          ref={handleRef}
          className="progress-handle"
          style={{
            transform: "translate(-50%, -50%) scaleX(0)",
            left: "var(--handle-x, 0px)",
          }}
        />
        <ReactTooltip
          className="progress-tooltip"
          arrowColor="inherit"
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
          <span>{millisecondsToStr(progressMs)}</span>
          <span className="divider">&#8239;/&#8239;</span>
          <span>{millisecondsToStr(durationMs)}</span>
        </div>
      )}
    </div>
  );
}

export default ProgressBar;
