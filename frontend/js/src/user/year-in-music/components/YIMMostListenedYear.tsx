import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import Tooltip from "react-tooltip";
import { ResponsiveBar } from "@nivo/bar";
// eslint-disable-next-line import/no-extraneous-dependencies
import { type AxisLegendPosition } from "@nivo/axes";
import { isEmpty, range, uniq } from "lodash";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { useMediaQuery } from "../../../explore/fresh-releases/utils";

type YIMGenreGraphProps = {
  mostListenedYearData: { [key: string]: number };
  userName: string;
  gradientColors: string[];
};
export default function YIMGenreGraph(props: YIMGenreGraphProps) {
  const { mostListenedYearData, userName, gradientColors } = props;
  const { currentUser } = React.useContext(GlobalAppContext);
  const isMobile = useMediaQuery("(max-width: 767px)");
  const isCurrentUser = userName === currentUser?.name;
  const yourOrUsersName = isCurrentUser ? "your" : `${userName}'s`;
  if (isEmpty(mostListenedYearData)) {
    return null;
  }
  const mostListenedYears = Object.keys(mostListenedYearData);
  const filledYears = range(
    Number(mostListenedYears[0]),
    Number(mostListenedYears[mostListenedYears.length - 1]) + 1
  );
  const mostListenedYearDataForGraph = filledYears.map(
    (listenYear: number) => ({
      year: listenYear,
      songs: String(mostListenedYearData[String(listenYear)] ?? 0),
    })
  );
  const mostListenedYearYears = uniq(
    mostListenedYearDataForGraph.map((datum) => datum.year)
  );
  const mostListenedMaxYear = Math.max(...mostListenedYearYears);
  const mostListenedMinYear = Math.min(...mostListenedYearYears);
  const modulus = isMobile ? 2 : 5;
  const mostListenedYearTicks = uniq(
    mostListenedYearYears
      .map((listenYear) => Math.round((listenYear + 1) / modulus) * modulus)
      .filter(
        (listenYear) =>
          listenYear >= mostListenedMinYear && listenYear <= mostListenedMaxYear
      )
  );
  const mobileMargins = { left: 40, bottom: 30, right: 15, top: 15 };
  const desktopMargins = { left: 50, bottom: 45, right: 30, top: 30 };
  const axis1 = {
    legend: "Number of listens",
    legendOffset: isMobile ? -5 : -40,
    legendPosition: "middle" as AxisLegendPosition,
  };
  const axis2 = {
    tickValues: mostListenedYearTicks,
    tickRotation: -30,
  };
  return (
    <div className="" id="most-listened-year">
      <h3 className="text-center">
        What year are {yourOrUsersName} favorite songs from?{" "}
        <FontAwesomeIcon
          icon={faQuestionCircle}
          data-tip
          data-for="most-listened-year-helptext"
          size="xs"
        />
        <Tooltip id="most-listened-year-helptext">
          How much {isCurrentUser ? "were you" : `was ${userName}`} on the
          lookout for new music this year? Not that we&apos;re judging
        </Tooltip>
      </h3>
      <div className="graph-container card-bg">
        <div className="graph">
          <ResponsiveBar
            margin={isMobile ? mobileMargins : desktopMargins}
            data={mostListenedYearDataForGraph}
            padding={0.1}
            layout={isMobile ? "horizontal" : "vertical"}
            keys={["songs"]}
            indexBy="year"
            colors={gradientColors}
            enableLabel={false}
            axisBottom={isMobile ? axis1 : axis2}
            axisLeft={isMobile ? axis2 : axis1}
          />
        </div>
      </div>
    </div>
  );
}
