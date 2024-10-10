import {
  faChevronLeft,
  faChevronRight,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { throttle } from "lodash";
import React, { PropsWithChildren } from "react";
import { useDraggable } from "react-use-draggable-scroll-safe";

type HorizontalScrollContainerProps = {
  showScrollbar?: Boolean;
  enableDragScroll?: Boolean;
  className?: string;
};

// How many pixels do the arrow buttons scroll?
const MANUAL_SCROLL_AMOUNT = 500;

export default function HorizontalScrollContainer({
  showScrollbar = true,
  enableDragScroll = true,
  className,
  children,
}: PropsWithChildren<HorizontalScrollContainerProps>) {
  const scrollContainerRef = React.useRef<HTMLDivElement>(null);

  const { events } = useDraggable(scrollContainerRef, {
    applyRubberBandEffect: true,
  });

  const onMouseDown: React.MouseEventHandler<HTMLElement> = (event) => {
    // Call the use-draggable-scroll-safe hook event
    events.onMouseDown(event);
    // Set our own class to allow for snap-scroll
    (event.target as HTMLElement)?.parentElement?.classList.add("dragging");
  };
  const onMouseUp: React.MouseEventHandler<HTMLElement> = (event) => {
    (event.target as HTMLElement)?.parentElement?.classList.remove("dragging");
  };

  const onScroll: React.ReactEventHandler<HTMLElement> = (event) => {
    const element = event.target as HTMLElement;
    const parent = element.parentElement;
    if (!element || !parent) {
      return;
    }

    if (element.scrollWidth - element.scrollLeft >= MANUAL_SCROLL_AMOUNT) {
      parent.classList.add("scroll-end");
      parent.classList.remove("scroll-start");
    } else if (element.scrollLeft <= MANUAL_SCROLL_AMOUNT) {
      parent.classList.add("scroll-start");
      parent.classList.remove("scroll-end");
    } else {
      parent.classList.remove("scroll-end");
      parent.classList.remove("scroll-start");
    }
  };
  const throttledOnScroll = throttle(onScroll, 400, { leading: true });

  const onManualScroll: React.ReactEventHandler<HTMLElement> = (event) => {
    if (!scrollContainerRef?.current) {
      return;
    }
    if (event?.currentTarget.classList.contains("forward")) {
      scrollContainerRef.current.scrollBy({
        left: MANUAL_SCROLL_AMOUNT,
        top: 0,
        behavior: "smooth",
      });
    } else {
      scrollContainerRef.current.scrollBy({
        left: -MANUAL_SCROLL_AMOUNT,
        top: 0,
        behavior: "smooth",
      });
    }
    // Also call the onScroll (throttled) event to ensure
    // the expected CSS classes are applied to the container
    throttledOnScroll(event);
  };

  return (
    <div className="horizontal-scroll-container scroll-start">
      <button
        className="nav-button backward"
        type="button"
        onClick={onManualScroll}
        tabIndex={0}
      >
        <FontAwesomeIcon icon={faChevronLeft} />
      </button>
      <div
        className={`horizontal-scroll ${
          showScrollbar ? "small-scrollbar" : "no-scrollbar"
        } ${className ?? ""}`}
        onScroll={throttledOnScroll}
        onMouseDown={enableDragScroll ? onMouseDown : undefined}
        onMouseUp={enableDragScroll ? onMouseUp : undefined}
        ref={scrollContainerRef}
        role="grid"
        tabIndex={-2}
      >
        {children}
      </div>
      <button
        className="nav-button forward"
        type="button"
        onClick={onManualScroll}
        tabIndex={0}
      >
        <FontAwesomeIcon icon={faChevronRight} />
      </button>
    </div>
  );
}
