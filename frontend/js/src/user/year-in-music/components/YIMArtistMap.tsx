import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { isEmpty } from "lodash";
import * as React from "react";
import Tooltip from "react-tooltip";
import tinycolor from "tinycolor2";
import CustomChoropleth from "../../stats/components/Choropleth";

export type YIMArtistMapData = Array<{
  country: string;
  artist_count: number;
  listen_count: number;
  artists: Array<UserArtistMapArtist>;
}>;
type YIMArtistMapProps = {
  yourOrUsersName: string;
  artistMapData: YIMArtistMapData;
  gradientColors: string[];
};

export default function YIMArtistMap(props: YIMArtistMapProps) {
  const { yourOrUsersName, artistMapData, gradientColors } = props;
  const [selectedMetric, setSelectedMetric] = React.useState<
    "artist" | "listen"
  >("listen");
  const changeSelectedMetric = (
    newSelectedMetric: "artist" | "listen",
    event?: React.MouseEvent<HTMLElement>
  ) => {
    if (event) {
      event.preventDefault();
    }
    setSelectedMetric(newSelectedMetric);
  };
  const artistMapDataForGraph = artistMapData?.map((country) => ({
    id: country.country,
    value:
      selectedMetric === "artist" ? country.artist_count : country.listen_count,
    artists: country.artists,
  }));
  if (isEmpty(artistMapData)) {
    return null;
  }
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
    <div className="" id="user-artist-map" style={{ marginTop: "1.5em" }}>
      <h3 className="text-center">
        What countries are {yourOrUsersName} favorite artists from?{" "}
        <FontAwesomeIcon
          icon={faQuestionCircle}
          data-tip
          data-for="user-artist-map-helptext"
          size="xs"
        />
        <Tooltip id="user-artist-map-helptext">
          Click on a country to see more details
        </Tooltip>
      </h3>
      <div className="graph-container card-bg">
        <div className="graph">
          <div style={{ paddingLeft: "3em" }}>
            <span>Rank by number of</span>
            <span className="dropdown">
              <button
                className="dropdown-toggle btn-transparent capitalize-bold"
                data-bs-toggle="dropdown"
                type="button"
              >
                {selectedMetric}s
                <span className="caret" />
              </button>
              <ul className="dropdown-menu" role="menu">
                <button
                  type="button"
                  className={`dropdown-item ${
                    selectedMetric === "listen" ? "active" : undefined
                  }`}
                  onClick={(event) => changeSelectedMetric("listen", event)}
                >
                  Listens
                </button>
                <button
                  type="button"
                  className={`dropdown-item ${
                    selectedMetric === "artist" ? "active" : undefined
                  }`}
                  onClick={(event) => changeSelectedMetric("artist", event)}
                >
                  Artists
                </button>
              </ul>
            </span>
          </div>
          <CustomChoropleth
            data={artistMapDataForGraph}
            selectedMetric={selectedMetric}
            colorScaleRange={colorPalette}
          />
        </div>
      </div>
    </div>
  );
}
