import * as React from "react";
import tinycolor from "tinycolor2";
import { isEmpty, isEqual } from "lodash";
import SimilarTracksGraph from "./SimilarTracksGraph";
import generateTransformedTracks from "../utils/generateTransformedTracks";

type SimilarTracksProps = {
  onTrackChange: (recording_mbid: string) => void;
  trackGraphNodeInfo: TrackNodeInfo | undefined;
  similarTracksList: TrackNodeInfo[];
  topAlbumReleaseColor: ReleaseColor | undefined;
  topTrackReleaseColor: ReleaseColor | undefined;
  similarTracksLimit: number;
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

function SimilarTracks(props: SimilarTracksProps) {
  const {
    onTrackChange,
    trackGraphNodeInfo,
    similarTracksList,
    topAlbumReleaseColor,
    topTrackReleaseColor,
    similarTracksLimit,
    graphParentElementRef,
  } = props;

  const DEFAULT_COLORS = colorGenerator();
  const [trackColors, setTrackColors] = React.useState(DEFAULT_COLORS);

  const calculateNewTrackColors = React.useMemo(() => {
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
      topTrackReleaseColor &&
      !isEmpty(topTrackReleaseColor) &&
      !isEqual(topAlbumReleaseColor, topTrackReleaseColor)
    ) {
      const { red, green, blue } = topTrackReleaseColor;
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

    setTrackColors([firstColor, secondColor]);
  }, [
    topAlbumReleaseColor,
    topTrackReleaseColor,
    trackGraphNodeInfo?.recording_mbid,
  ]);

  const transformedTracks = React.useMemo(
    () =>
      trackGraphNodeInfo
        ? generateTransformedTracks(
            trackGraphNodeInfo,
            similarTracksList,
            trackColors[0],
            trackColors[1],
            similarTracksLimit
          )
        : {
            nodes: [],
            links: [],
          },
    [trackGraphNodeInfo, similarTracksList, trackColors, similarTracksLimit]
  );

  const backgroundGradient = React.useMemo(() => {
    const releaseHue = trackColors[0]
      .clone()
      .setAlpha(BACKGROUND_ALPHA)
      .toRgbString();
    const trackHue = trackColors[1]
      .clone()
      .setAlpha(BACKGROUND_ALPHA)
      .toRgbString();

    return `linear-gradient(180deg, ${releaseHue} 0%, ${trackHue} 100%)`;
  }, [trackColors]);

  return (
    <SimilarTracksGraph
      onTrackChange={onTrackChange}
      data={transformedTracks}
      background={backgroundGradient}
      graphParentElementRef={graphParentElementRef}
    />
  );
}

export default React.memo(SimilarTracks);
