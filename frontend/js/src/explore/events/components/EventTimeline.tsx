import * as React from "react";
import Slider from "rc-slider";
import { debounce, zipObject } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCalendarCheck } from "@fortawesome/free-solid-svg-icons";
import { startOfDay } from "date-fns";
import { getEventGroupKey, getEventLastDay, useMediaQuery } from "../utils";
import type { SortDirection } from "../EventsExplorer";
import { COLOR_LB_BLUE } from "../../../utils/constants";

type EventTimelineProps = {
  events: Array<ExplorerEventItem>;
  order: string;
  direction: SortDirection;
};

function createMarks(
  events: Array<ExplorerEventItem>,
  order: string,
  direction: SortDirection
) {
  // where each group of cards starts, as a percentage of the list
  const groups: Array<{ key: string; percent: number; count: number }> = [];
  events.forEach((event, index) => {
    const key = getEventGroupKey(order, event);
    const lastGroup = groups[groups.length - 1];
    if (lastGroup && lastGroup.key === key) {
      lastGroup.count += 1;
    } else {
      groups.push({ key, percent: (100 * index) / events.length, count: 1 });
    }
  });

  let dataArr: Array<string | JSX.Element> = [];
  let percentArr: Array<number> = [];

  if (order === "date") {
    // label the first group and the group nearest each tenth of the list
    const labelled = new Set([groups[0]]);
    for (let i = 10; i < 100; i += 10) {
      let nearest = groups[0];
      groups.forEach((group) => {
        if (Math.abs(group.percent - i) < Math.abs(nearest.percent - i)) {
          nearest = group;
        }
      });
      if (Math.abs(nearest.percent - i) < 10) {
        labelled.add(nearest);
      }
    }
    labelled.forEach((group) => {
      dataArr.push(group.key);
      percentArr.push(group.percent);
    });

    // the calendar marks where the list crosses from past events to upcoming ones
    const today = startOfDay(new Date());
    const isUpcoming = (event: ExplorerEventItem) =>
      (getEventLastDay(event) ?? today) >= today;
    const crossing = events.findIndex(
      (event) => isUpcoming(event) !== isUpcoming(events[0])
    );
    let todayPercent: number | undefined;
    if (crossing !== -1) {
      todayPercent = (100 * crossing) / events.length;
    } else if (isUpcoming(events[0]) === (direction === "ascend")) {
      todayPercent = 0;
    }
    if (todayPercent !== undefined) {
      const index = percentArr.indexOf(todayPercent);
      if (index !== -1) {
        dataArr.splice(index, 1);
        percentArr.splice(index, 1);
      }
      dataArr.push(
        <FontAwesomeIcon
          icon={faCalendarCheck}
          size="2xl"
          color={COLOR_LB_BLUE}
          title="Today"
        />
      );
      percentArr.push(todayPercent);
    }

    const sortedData = percentArr
      .map((percent, index) => ({ percent, data: dataArr[index] }))
      .sort((a, b) => a.percent - b.percent);

    dataArr = sortedData.map((item) => item.data);
    percentArr = sortedData.map((item) => item.percent);
  } else {
    // We want to filter out the keys that have less than 1.5% of the total events count
    const minEventsThreshold = Math.floor(events.length * 0.015);
    groups
      .filter(
        (group, index) => index === 0 || group.count >= minEventsThreshold
      )
      .forEach((group) => {
        dataArr.push(group.key);
        percentArr.push(group.percent);
      });
  }

  return zipObject(percentArr, dataArr);
}

export default function EventTimeline(props: EventTimelineProps) {
  const { events, order, direction } = props;

  const [currentValue, setCurrentValue] = React.useState<number | number[]>();
  const [marks, setMarks] = React.useState<{ [key: number]: React.ReactNode }>(
    {}
  );

  const screenMd = useMediaQuery("(max-width: 992px)"); // @screen-md

  const changeHandler = React.useCallback((percent: number | number[]) => {
    setCurrentValue(percent);
    const element: HTMLElement | null = document.getElementById(
      "events-explorer-grids"
    )!;
    const scrollHeight = ((percent as number) / 100) * element.scrollHeight;
    const scrollTo = scrollHeight + element.offsetTop;
    window.scrollTo({ top: scrollTo, behavior: "smooth" });
    return scrollTo;
  }, []);

  React.useEffect(() => {
    setMarks(createMarks(events, order, direction));
  }, [events, order, direction]);

  React.useEffect(() => {
    const handleScroll = debounce(() => {
      const container = document.getElementById("events-explorer-grids");
      if (!container) {
        return;
      }
      const scrollPos =
        ((window.scrollY - container.offsetTop) / container.scrollHeight) * 100;
      setCurrentValue(scrollPos);
    }, 500);

    window.addEventListener("scroll", handleScroll);
    return () => {
      handleScroll.cancel();
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  return (
    <div className="events-timeline">
      <Slider
        className={
          screenMd
            ? "events-timeline-slider-horizontal"
            : "events-timeline-slider-vertical"
        }
        vertical={!screenMd}
        reverse={!screenMd}
        included={false}
        marks={marks}
        value={currentValue}
        onChange={changeHandler}
      />
    </div>
  );
}
