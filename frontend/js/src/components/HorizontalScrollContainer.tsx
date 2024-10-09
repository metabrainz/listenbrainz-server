import {
  faChevronLeft,
  faChevronRight,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { throttle } from "lodash";
import React, { PropsWithChildren } from "react";

type HorizontalScrollContainerProps = {
  showScrollbar?: Boolean;
  scrollContainerCssClass?: string;
};

export default function HorizontalScrollContainer({
  showScrollbar = true,
  scrollContainerCssClass,
  children,
}: PropsWithChildren<HorizontalScrollContainerProps>) {
  const scrollContainerRef = React.useRef<HTMLDivElement>(null);

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
      >
        <FontAwesomeIcon icon={faChevronLeft} />
      </button>
      <div
        className={`horizontal-scroll ${scrollContainerCssClass ?? ""} ${
          showScrollbar ? "small-scrollbar" : "no-scrollbar"
        }`}
        onScroll={throttledOnScroll}
        ref={scrollContainerRef}
      >
        {children}
      </div>
      <button
        className="nav-button forward"
        type="button"
        onClick={manualScroll}
      >
        <FontAwesomeIcon icon={faChevronRight} />
      </button>
    </div>
  );
}
