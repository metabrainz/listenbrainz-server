import { isEmpty } from "lodash";
import * as React from "react";
import tinycolor from "tinycolor2";
import { UserArtistEvolutionActivityGraph } from "../../stats/components/UserArtistEvolutionActivity";

type YIMArtistEvolutionProps = {
  yourOrUsersName: string;
  artistEvolutionData: RawUserArtistEvolutionRow[];
  gradientColors: string[];
  year: number;
};

export default function YIMArtistEvolution(props: YIMArtistEvolutionProps) {
  const { yourOrUsersName, artistEvolutionData, gradientColors, year } = props;
  if (isEmpty(artistEvolutionData)) {
    return null;
  }
  const colorPalette = [
    ...Array.from(Array(10).keys()).map((index) =>
      tinycolor
        .mix(gradientColors[0], gradientColors[1], (index - 1) * 10)
        .saturate(10)
        .toHexString()
    ),
  ];
  return (
    <div className="" id="user-artist-map" style={{ marginTop: "1.5em" }}>
      <h3 className="text-center">
        Evolution of {yourOrUsersName} favorite artists of {year}
      </h3>
      <div className="graph-container card-bg">
        <div className="graph">
          <UserArtistEvolutionActivityGraph
            rawData={artistEvolutionData}
            range="this_year"
            colorPalette={colorPalette}
          />
        </div>
      </div>
    </div>
  );
}
