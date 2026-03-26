import {
  faChevronLeft,
  faChevronRight,
  faChevronUp,
  faChevronDown,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { throttle } from "lodash";
import React, { PropsWithChildren } from "react";
import { useDraggable } from "react-use-draggable-scroll-safe";

type HorizontalScrollContainerProps = {
  showScrollbar?: Boolean;
  enableDragScroll?: Boolean;
  className?: string;
  direction?: "horizontal" | "vertical";
};

// How many pixels do the arrow buttons scroll?
const MANUAL_SCROLL_AMOUNT = 500;

export default function HorizontalScrollContainer({
  showScrollbar = true,
  enableDragScroll = true,
  direction = "horizontal",
  className,
  children,
}: PropsWithChildren<HorizontalScrollContainerProps>) {
  const scrollContainerRef = React.useRef<HTMLDivElement>(null);

  const isVertical = direction === "vertical";

  const { events } = useDraggable(scrollContainerRef, {
    applyRubberBandEffect: true,
  });
  const { onMouseDown: draggableOnMouseDown } = events;

  const onMouseDown: React.MouseEventHandler<HTMLElement> = React.useCallback(
    (event) => {
      // Call the use-draggable-scroll-safe hook event
      draggableOnMouseDown(event);
      // Set our own class to allow for snap-scroll
      (event.target as HTMLElement)
        ?.closest(".scroll-container")
        ?.classList.add("dragging");
    },
    [draggableOnMouseDown]
  );

  const onMouseUp: React.MouseEventHandler<HTMLElement> = React.useCallback(
    (event) => {
      (event.target as HTMLElement)
        ?.closest(".scroll-container")
        ?.classList.remove("dragging");
    },
    []
  );

  const onScroll = React.useCallback(() => {
    const element = scrollContainerRef?.current;
    const parent = element?.parentElement;
    if (!element || !parent) {
      return;
    }
    // Don't expect so big a scroll before showing nav arrows on smaller screen sizes
    const requiredMinimumScrollAmount = Math.min(
      MANUAL_SCROLL_AMOUNT / 2,
      isVertical ? element.clientHeight / 2 : element.clientWidth / 2
    );

    // Set up appropriate CSS classes to show or hide nav buttons
    if (
      isVertical
        ? element.scrollHeight <= element.clientHeight
        : element.scrollWidth <= element.clientWidth
    ) {
      parent.classList.add("no-scroll");
    }
    parent.classList.remove("scroll-end");
    parent.classList.remove("scroll-start");

    if (
      isVertical
        ? element.scrollTop < requiredMinimumScrollAmount
        : element.scrollLeft < requiredMinimumScrollAmount
    ) {
      // We are at the beginning of the container and haven't scrolled more than requiredMinimumScrollAmount
      parent.classList.add("scroll-start");
    } else if (
      isVertical
        ? element.scrollHeight - element.scrollTop - element.clientHeight <=
          requiredMinimumScrollAmount - 2
        : element.scrollWidth - element.scrollLeft - element.clientWidth <=
          requiredMinimumScrollAmount - 2
    ) {
      parent.classList.add("scroll-end");
    }
  }, [isVertical]);

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
          left: isVertical ? 0 : MANUAL_SCROLL_AMOUNT,
          top: isVertical ? MANUAL_SCROLL_AMOUNT : 0,
          behavior: "smooth",
        });
      } else {
        scrollContainerRef.current.scrollBy({
          left: isVertical ? 0 : -MANUAL_SCROLL_AMOUNT,
          top: isVertical ? -MANUAL_SCROLL_AMOUNT : 0,
          behavior: "smooth",
        });
      }
      // Also call the onScroll (throttled) event to ensure
      // the expected CSS classes are applied to the container
      throttledOnScroll();
    },
    [isVertical, throttledOnScroll]
  );

  React.useEffect(() => {
    // Run once on startup to set up expected CSS classes applied to the container
    onScroll();
  }, []);

  return (
    <div
      className={
        isVertical
          ? "scroll-container vertical"
          : "scroll-container horizontal horizontal-scroll-container"
      }
    >
      <button
        className="nav-button backward"
        type="button"
        onClick={onManualScroll}
        tabIndex={0}
      >
        <FontAwesomeIcon icon={isVertical ? faChevronUp : faChevronLeft} />
      </button>
      <div
        className={`${isVertical ? "vertical-scroll" : "horizontal-scroll"} ${
          showScrollbar ? "small-scrollbar" : "no-scrollbar"
        } ${className ?? ""}`}
        onScroll={throttledOnScroll}
        onMouseDown={!isVertical && enableDragScroll ? onMouseDown : undefined}
        onMouseUp={!isVertical && enableDragScroll ? onMouseUp : undefined}
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
        <FontAwesomeIcon icon={isVertical ? faChevronDown : faChevronRight} />
      </button>
    </div>
  );
}
