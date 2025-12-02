import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { ResponsiveTreeMap } from "@nivo/treemap";
import * as React from "react";
import Tooltip from "react-tooltip";
import GlobalAppContext from "../../../utils/GlobalAppContext";

type Node = {
  id: string;
  loc: number;
  name: string;
  children?: Node[];
};
export type GenreGraphDataT = {
  children: Node[];
  name: string;
};
type YIMGenreGraphProps = {
  genreGraphData: GenreGraphDataT;
  userName: string;
};
export default function YIMGenreGraph(props: YIMGenreGraphProps) {
  const { genreGraphData, userName } = props;
  const { currentUser } = React.useContext(GlobalAppContext);
  const isCurrentUser = userName === currentUser?.name;
  const youOrUsername = isCurrentUser ? "you" : `${userName}`;
  const hasOrHave = isCurrentUser ? "have" : "has";
  return (
    <div className="" id="genre-graph">
      <h3 className="text-center">
        What genres {hasOrHave} {youOrUsername} explored?{" "}
        <FontAwesomeIcon
          icon={faQuestionCircle}
          data-tip
          data-for="genre-graph-helptext"
          size="xs"
        />
        <Tooltip id="genre-graph-helptext">
          The top genres {youOrUsername} listened to this year
        </Tooltip>
      </h3>
      <div className="graph-container card-bg">
        <div className="graph" style={{ height: "400px" }}>
          <ResponsiveTreeMap
            margin={{ left: 30, bottom: 30, right: 30, top: 30 }}
            data={genreGraphData}
            identity="name"
            value="loc"
            valueFormat=".02s"
            label="id"
            labelSkipSize={12}
            labelTextColor={{
              from: "color",
              modifiers: [["darker", 1.2]],
            }}
            // colors={reorderedColors}
            parentLabelPosition="left"
            parentLabelTextColor={{
              from: "color",
              modifiers: [["darker", 2]],
            }}
            borderColor={{
              from: "color",
              modifiers: [["darker", 0.1]],
            }}
          />
        </div>
      </div>
    </div>
  );
}
