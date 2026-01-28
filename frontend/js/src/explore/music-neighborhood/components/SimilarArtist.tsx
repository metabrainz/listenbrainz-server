import * as React from "react";
import tinycolor from "tinycolor2";
import { isEmpty, isEqual } from "lodash";
import SimilarArtistsGraph from "./SimilarArtistsGraph";
import generateTransformedArtists from "../utils/generateTransformedArtists";

type SimilarArtistProps = {
  onArtistChange: (artist_mbid: string) => void;
  artistGraphNodeInfo: ArtistNodeInfo | undefined;
  similarArtistsList: ArtistNodeInfo[];
  topAlbumReleaseColor: ReleaseColor | undefined;
  topRecordingReleaseColor: ReleaseColor | undefined;
  similarArtistsLimit: number;
  graphParentElementRef: React.RefObject<HTMLDivElement>;
};

const BACKGROUND_ALPHA = 0.2;
const MAXIMUM_LUMINANCE = 0.8;
const MINIMUM_LUMINANCE = 0.2;

const colorGenerator = (): [tinycolor.Instance, tinycolor.Instance] => {
  const initialColor = tinycolor(`hsv(${Math.random() * 360}, 100%, 90%)`);
  return [initialColor, initialColor.clone().tetrad()[1]];
};

const isColorTooLight = (color: tinycolor.Instance): boolean => {
  return color.getLuminance() > MAXIMUM_LUMINANCE;
};
const isColorTooDark = (color: tinycolor.Instance): boolean => {
  return color.getLuminance() < MINIMUM_LUMINANCE;
};

function SimilarArtist(props: SimilarArtistProps) {
  const {
    onArtistChange,
    artistGraphNodeInfo,
    similarArtistsList,
    topAlbumReleaseColor,
    topRecordingReleaseColor,
    similarArtistsLimit,
    graphParentElementRef,
  } = props;

  const DEFAULT_COLORS = colorGenerator();
  const [artistColors, setArtistColors] = React.useState(DEFAULT_COLORS);

  const calculateNewArtistColors = React.useMemo(() => {
    let firstColor;
    let secondColor;
    if (topAlbumReleaseColor && !isEmpty(topAlbumReleaseColor)) {
      const { red, green, blue } = topAlbumReleaseColor;
      firstColor = tinycolor({ r: red, g: green, b: blue });
    } else {
      // Do we want to pick a color from an array of predefined colors instead of random?
      firstColor = tinycolor.random();
    }
    if (
      topRecordingReleaseColor &&
      !isEmpty(topRecordingReleaseColor) &&
      !isEqual(topAlbumReleaseColor, topRecordingReleaseColor)
    ) {
      const { red, green, blue } = topRecordingReleaseColor;
      secondColor = tinycolor({ r: red, g: green, b: blue });
      // We should consider using another color library that allows us to calculate color distance
      // better using deltaE algorithms. Looks into color.js and chroma.js for example.
      const hue1 = firstColor.toHsv().h;
      const hue2 = secondColor.toHsv().h;
      const distanceBetweenColors = Math.min(
        Math.abs(hue2 - hue1),
        360 - Math.abs(hue2 - hue1)
      );
      if (distanceBetweenColors < 25) {
        // Colors are too similar, set up for picking another color below.
        secondColor = undefined;
      }
    }
    if (!secondColor) {
      // If we don't have required release info, base the second color on the first,
      // randomly picking one of the tetrad complementary colors.
      const randomTetradColor = Math.round(Math.random() * (3 - 1) + 1);
      secondColor = tinycolor(firstColor).clone().tetrad()[randomTetradColor];
    }

    // Adjust the colors if they are too light or too dark
    [firstColor, secondColor].forEach((color) => {
      if (isColorTooLight(color)) {
        color.darken(20).saturate(30);
      } else if (isColorTooDark(color)) {
        color.lighten(20).saturate(30);
      }
    });

    setArtistColors([firstColor, secondColor]);
  }, [topAlbumReleaseColor, topRecordingReleaseColor]);

  const transformedArtists = React.useMemo(
    () =>
      artistGraphNodeInfo
        ? generateTransformedArtists(
            artistGraphNodeInfo,
            similarArtistsList,
            artistColors[0],
            artistColors[1],
            similarArtistsLimit
          )
        : {
            nodes: [],
            links: [],
          },
    [artistGraphNodeInfo, similarArtistsList, artistColors, similarArtistsLimit]
  );

  const backgroundGradient = React.useMemo(() => {
    const releaseHue = artistColors[0]
      .clone()
      .setAlpha(BACKGROUND_ALPHA)
      .toRgbString();
    const recordingHue = artistColors[1]
      .clone()
      .setAlpha(BACKGROUND_ALPHA)
      .toRgbString();

    return `linear-gradient(180deg, ${releaseHue} 0%, ${recordingHue} 100%)`;
  }, [artistColors]);

  return (
    <SimilarArtistsGraph
      onArtistChange={onArtistChange}
      data={transformedArtists}
      background={backgroundGradient}
      graphParentElementRef={graphParentElementRef}
    />
  );
}

export default React.memo(SimilarArtist);
