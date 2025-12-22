import { isEmpty } from "lodash";
import * as React from "react";
import { UserGenreActivityGraph } from "../../stats/components/UserGenreActivity";

type YIMGenreActivityProps = {
  yourOrUsersName: string;
  genreActivityData: GenreHourData[];
  gradientColors: string[];
  year: number;
};

export default function YIMGenreActivity(props: YIMGenreActivityProps) {
  const { yourOrUsersName, genreActivityData, gradientColors, year } = props;
  if (isEmpty(genreActivityData)) {
    return null;
  }

  return (
    <div className="" id="user-genre-activity" style={{ marginTop: "1.5em" }}>
      <h3 className="text-center">
        What genres do you listen to throughout the day?
      </h3>
      <div className="graph-container card-bg">
        <div className="graph">
          <UserGenreActivityGraph
            rawData={genreActivityData}
          />
        </div>
      </div>
    </div>
  );
}
