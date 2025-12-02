import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import Tooltip from "react-tooltip";
import { ResponsiveBar } from "@nivo/bar";
import { isEmpty, range, uniq } from "lodash";
import GlobalAppContext from "../../../utils/GlobalAppContext";

type YIMGenreGraphProps = {
  mostListenedYearData: { [key: string]: number };
  userName: string;
};
export default function YIMGenreGraph(props: YIMGenreGraphProps) {
  const { mostListenedYearData, userName } = props;
  const { currentUser } = React.useContext(GlobalAppContext);
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
  const mostListenedYearTicks = uniq(
    mostListenedYearYears
      .map((listenYear) => Math.round((listenYear + 1) / 5) * 5)
      .filter(
        (listenYear) =>
          listenYear >= mostListenedMinYear && listenYear <= mostListenedMaxYear
      )
  );
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
            margin={{ left: 50, bottom: 45, right: 30, top: 30 }}
            data={mostListenedYearDataForGraph}
            padding={0.1}
            layout="vertical"
            keys={["songs"]}
            indexBy="year"
            // colors={accentColor}
            enableLabel={false}
            axisBottom={{
              tickValues: mostListenedYearTicks,
              tickRotation: -30,
            }}
            axisLeft={{
              legend: "Number of listens",
              legendOffset: -40,
              legendPosition: "middle",
            }}
          />
        </div>
      </div>
    </div>
  );
}
