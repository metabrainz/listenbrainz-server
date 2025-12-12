import { capitalize, isEmpty } from "lodash";
import React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import Tooltip from "react-tooltip";
import { CalendarDatum, ResponsiveCalendar } from "@nivo/calendar";
import tinycolor from "tinycolor2";
import GlobalAppContext from "../../../utils/GlobalAppContext";

export type YIMListeningActivityData = Array<{
  to_ts: number;
  from_ts: number;
  time_range: string;
  listen_count: number;
}>;
type YIMListeningActivityProps = {
  listensPerDay: YIMListeningActivityData;
  userName: string;
  year: number;
  gradientColors: string[];
};
export default function YIMListeningActivity({
  listensPerDay,
  userName,
  year,
  gradientColors,
}: YIMListeningActivityProps) {
  const { currentUser } = React.useContext(GlobalAppContext);
  const isCurrentUser = userName === currentUser?.name;
  const youOrUsername = isCurrentUser ? "you" : `${userName}`;
  const yourOrUsersName = isCurrentUser ? "your" : `${userName}'s`;
  /* Listening history calendar graph */
  if (isEmpty(listensPerDay)) {
    return null;
  }
  const listensPerDayForGraph = listensPerDay
    .map((datum) =>
      datum.listen_count > 0
        ? {
            day: new Date(datum.time_range).toLocaleDateString("en-CA"),
            value: datum.listen_count,
          }
        : null
    )
    .filter(Boolean);
  const colorPalette = [
    ...[1, 2, 3, 4, 5]
      .map((index) =>
        tinycolor(gradientColors[1])
          .lighten(10 * index)
          .toHexString()
      )
      .reverse(),
    gradientColors[1],
  ];
  return (
    <div className="" id="calendar">
      <h3 className="text-center">
        {capitalize(yourOrUsersName)} listening activity{" "}
        <FontAwesomeIcon
          icon={faQuestionCircle}
          data-tip
          data-for="listening-activity"
          size="xs"
        />
        <Tooltip id="listening-activity">
          How many tracks did {youOrUsername} listen to each day of the year?
        </Tooltip>
      </h3>

      <div className="graph-container card-bg">
        <div className="graph">
          <ResponsiveCalendar
            from={`${year}-01-01`}
            to={`${year}-12-31`}
            data={listensPerDayForGraph as CalendarDatum[]}
            // emptyColor={selectedSeason.background}
            colors={colorPalette}
            monthBorderColor="#eeeeee"
            dayBorderWidth={1}
            dayBorderColor="#ffffff"
            legends={[
              {
                anchor: "bottom-left",
                direction: "row",
                itemCount: 4,
                itemWidth: 42,
                itemHeight: 36,
                itemsSpacing: 14,
                itemDirection: "right-to-left",
              },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
