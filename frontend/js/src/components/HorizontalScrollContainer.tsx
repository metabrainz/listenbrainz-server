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
  const { onMouseDown: draggableOnMouseDown } = events;

  const onMouseDown: React.MouseEventHandler<HTMLElement> = React.useCallback(
    (event) => {
      // Call the use-draggable-scroll-safe hook event
      draggableOnMouseDown(event);
      // Set our own class to allow for snap-scroll
      (event.target as HTMLElement)?.parentElement?.classList.add("dragging");
    },
    [draggableOnMouseDown]
  );

  const onMouseUp: React.MouseEventHandler<HTMLElement> = React.useCallback(
    (event) => {
      (event.target as HTMLElement)?.parentElement?.classList.remove(
        "dragging"
      );
    },
    []
  );

  const onScroll = React.useCallback(() => {
    const element = scrollContainerRef?.current;
    const parent = element?.parentElement;
    if (!element || !parent) {
      return;
    }

    parent.classList.remove("scroll-end");
    parent.classList.remove("scroll-start");

    if (element.scrollLeft < MANUAL_SCROLL_AMOUNT) {
      // We are at the beginning of the container and haven't scrolled more than MANUAL_SCROLL_AMOUNT
      parent.classList.add("scroll-start");
    } else if (
      // We have scrolled to the end of the container, i.e. there is less than MANUAL_SCROLL_AMOUNT before the end of the scroll
      // (with a 2px adjustement)
      element.scrollWidth - element.scrollLeft - element.clientWidth <=
      MANUAL_SCROLL_AMOUNT - 2
    ) {
      parent.classList.add("scroll-end");
    }
  }, []);

  const throttledOnScroll = React.useMemo(
    () => throttle(onScroll, 400, { leading: true }),
    [onScroll]
  );

  const onManualScroll: React.ReactEventHandler<HTMLElement> = React.useCallback(
    (event) => {
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
      throttledOnScroll();
    },
    [throttledOnScroll]
  );

  React.useEffect(() => {
    // Run once on startup to set up expected CSS classes applied to the container
    onScroll();
  }, []);

  return (
    <div className="horizontal-scroll-container">
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
