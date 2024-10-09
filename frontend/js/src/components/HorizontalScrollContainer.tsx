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
  scrollContainerCssClass?: string;
};

export default function HorizontalScrollContainer({
  showScrollbar = true,
  enableDragScroll = true,
  scrollContainerCssClass,
  children,
}: PropsWithChildren<HorizontalScrollContainerProps>) {
  const scrollContainerRef = React.useRef<HTMLDivElement>(null);

  const { events } = useDraggable(scrollContainerRef, {
    applyRubberBandEffect: true,
  });

  const onMouseDown: React.MouseEventHandler<HTMLDivElement> = (event) => {
    // Call the dragScrolluse-draggable-safe hook event
    events.onMouseDown(event);
    // Set our own class to allow for snap-scroll
    (event.target as HTMLDivElement)?.parentElement?.classList.add("dragging");
  };
  const onMouseUp: React.MouseEventHandler<HTMLDivElement> = (event) => {
    (event.target as HTMLDivElement)?.parentElement?.classList.remove(
      "dragging"
    );
  };

  const onScroll: React.ReactEventHandler<HTMLDivElement> = (event) => {
    const element = event.target as HTMLDivElement;
    const parent = element.parentElement;
    if (!element || !parent) {
      return;
    }
    // calculate horizontal scroll percentage
    const scrollPercentage =
      (100 * element.scrollLeft) / (element.scrollWidth - element.clientWidth);

    if (scrollPercentage > 95) {
      parent.classList.add("scroll-end");
      parent.classList.remove("scroll-start");
    } else if (scrollPercentage < 5) {
      parent.classList.add("scroll-start");
      parent.classList.remove("scroll-end");
    } else {
      parent.classList.remove("scroll-end");
      parent.classList.remove("scroll-start");
    }
  };

  const manualScroll: React.ReactEventHandler<HTMLElement> = (event) => {
    if (!scrollContainerRef?.current) {
      return;
    }
    if (event?.currentTarget.classList.contains("forward")) {
      scrollContainerRef.current.scrollBy({
        left: 300,
        top: 0,
        behavior: "smooth",
      });
    } else {
      scrollContainerRef.current.scrollBy({
        left: -300,
        top: 0,
        behavior: "smooth",
      });
    }
  };

  const throttledOnScroll = throttle(onScroll, 400, { leading: true });

  return (
    <div className="horizontal-scroll-container scroll-start">
      <button
        className="nav-button backward"
        type="button"
        onClick={manualScroll}
        tabIndex={0}
      >
        <FontAwesomeIcon icon={faChevronLeft} />
      </button>
      <div
        className={`horizontal-scroll ${scrollContainerCssClass ?? ""} ${
          showScrollbar ? "small-scrollbar" : "no-scrollbar"
        }`}
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
        onClick={manualScroll}
        tabIndex={0}
      >
        <FontAwesomeIcon icon={faChevronRight} />
      </button>
    </div>
  );
}
