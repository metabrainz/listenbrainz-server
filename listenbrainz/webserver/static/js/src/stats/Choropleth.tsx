import { Theme } from "@nivo/core";
import { Choropleth } from "@nivo/geo";
import { BoxLegendSvg, LegendProps } from "@nivo/legends";
import { BasicTooltip } from "@nivo/tooltip";
import { scaleThreshold } from "d3-scale";
import { schemeOranges } from "d3-scale-chromatic";
import { format } from "d3-format";
import { maxBy } from "lodash";
import * as React from "react";
import { useMediaQuery } from "react-responsive";
import * as worldCountries from "./world_countries.json";

export type ChoroplethProps = {
  data: UserArtistMapData;
  width?: number;
  selectedMetric: "artist" | "listen";
};

export default function CustomChoropleth(props: ChoroplethProps) {
  const isMobile = useMediaQuery({ maxWidth: 767 });

  const commonLegendProps = {
    anchor: "bottom-left",
    direction: "column",
    itemDirection: "left-to-right",
    itemOpacity: 0.85,
    effects: [
      {
        on: "hover",
        style: {
          itemTextColor: "#000000",
          itemOpacity: 1,
        },
      },
    ],
  } as LegendProps;

  const legends = {
    desktop: {
      itemWidth: 90,
      itemHeight: 18,
      symbolSize: 18,
      translateX: 50,
      translateY: -50,
      ...commonLegendProps,
    } as LegendProps,
    mobile: {
      itemWidth: 90,
      itemHeight: 10,
      symbolSize: 10,
      translateX: 20,
      translateY: -15,
      ...commonLegendProps,
    } as LegendProps,
  };

  const themes: {
    desktop: Theme;
    mobile: Theme;
  } = {
    desktop: {
      legends: {
        text: {
          fontSize: 12,
        },
      },
    },
    mobile: {
      legends: {
        text: {
          fontSize: 8,
        },
      },
    },
  };

  const { data } = props;
  let { width } = props;
  width = width || 1200; // Set default width to 1200
  const height = width / 2;

  // Calculate logarithmic domain
  const domain = (() => {
    const maxArtistCount = maxBy(data, (datum) => datum.value)?.value || 1;

    const result = [];
    for (let i = 0; i < 6; i += 1) {
      result.push(
        Math.ceil(Math.E ** ((Math.log(maxArtistCount) / 6) * (i + 1)))
      );
    }

    return result;
  })();

  const colorScale = scaleThreshold<number, string>()
    .domain(domain)
    .range(schemeOranges[6]);

  // Create a custom legend component because the default doesn't work with scaleThreshold
  const CustomLegend = () => (
    <BoxLegendSvg
      containerHeight={height}
      containerWidth={width!}
      data={colorScale.range().map((color, index) => {
        // eslint-disable-next-line prefer-const
        let [start, end] = colorScale.invertExtent(color);

        // Domain starts with 1
        if (start === undefined) {
          start = 1;
        }

        return {
          index,
          color,
          id: color,
          extent: [start, end],
          label: `${format(".2s")(start)} - ${format(".2s")(end!)}`,
        };
      })}
      {...(isMobile ? legends.mobile : legends.desktop)}
    />
  );

  const CustomTooltip = ({ feature }: { feature: any }) => {
    if (feature.data === undefined) {
      return null;
    }

    const { selectedMetric } = props;
    let suffix = `${selectedMetric[0].toUpperCase()}${selectedMetric.slice(1)}`;
    if (feature.formattedValue !== "1") {
      suffix = `${suffix}s`;
    }

    return (
      <BasicTooltip
        id={feature.label}
        color={feature.color}
        value={`${feature.formattedValue} ${suffix}`}
        enableChip
      />
    );
  };

  return (
    <Choropleth
      data={data}
      width={width}
      height={height}
      features={worldCountries.features}
      margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
      colors={colorScale}
      domain={domain}
      theme={isMobile ? themes.mobile : themes.desktop}
      valueFormat=".2~s"
      tooltip={(feature) => {
        const tooltipData = feature.feature.data;
        return (
          <div>
            {tooltipData.artists.map((artist: UserArtistMapArtist) => (
              <p>
                <a
                  href={`https://musicbrainz.org/artist/${artist.artist_mbid}`}
                >
                  {artist.artist_name}
                </a>
                : {artist.listen_count}
              </p>
            ))}
          </div>
        );
      }}
      unknownColor="#efefef"
      label="properties.name"
      projectionScale={width / 5.5}
      projectionType="naturalEarth1"
      projectionTranslation={[0.5, 0.53]}
      borderWidth={0.5}
      borderColor="#152538"
      // The typescript definition file for Choropleth is incomplete, so disable typescript
      // until it is fixed.
      // @ts-ignore
      layers={["features", CustomLegend]}
    />
  );
}
