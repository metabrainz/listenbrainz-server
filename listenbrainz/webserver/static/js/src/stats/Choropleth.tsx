import { Theme } from "@nivo/core";
import { Choropleth } from "@nivo/geo";
import { BoxLegendSvg, LegendProps } from "@nivo/legends";
import { scaleThreshold } from "d3-scale";
import { schemeOranges } from "d3-scale-chromatic";
import * as _ from "lodash";
import * as React from "react";
import { useMediaQuery } from "react-responsive";
import * as features from "./world_countries.json";

export type ChoroplethProps = {
  data: UserArtistMapData;
  width?: number;
};

const CustomLegend = ({
  height,
  legends,
  width,
}: {
  height: number;
  legends: Array<LegendProps>;
  width: any;
}) => (
  <>
    {legends.map((legend) => (
      <BoxLegendSvg
        key={JSON.stringify(legend.data?.map(({ id }) => id))}
        containerHeight={height}
        containerWidth={width}
        {...legend}
      />
    ))}
  </>
);

export default function CustomChoropleth(props: ChoroplethProps) {
  const isMobile = useMediaQuery({ maxWidth: 767 });

  const commonLegendProps: Partial<LegendProps> = {
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
  };
  const legends = {
    desktop: {
      itemWidth: 90,
      itemHeight: 18,
      symbolSize: 18,
      translateX: 50,
      translateY: -50,
      ...commonLegendProps,
    },
    mobile: {
      itemWidth: 90,
      itemHeight: 10,
      symbolSize: 10,
      translateX: 20,
      translateY: -15,
      ...commonLegendProps,
    },
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

  // Calculate logarithmic domain
  const domain = (() => {
    const maxArtistCount = _.maxBy(data, (datum) => datum.value)?.value || 1;

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

  return (
    <Choropleth
      data={data}
      width={width}
      height={width * 0.5}
      features={features.features}
      margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
      colors={colorScale}
      domain={domain}
      theme={isMobile ? themes.mobile : themes.desktop}
      valueFormat=".2s"
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
      legends={[isMobile ? legends.mobile : legends.desktop]}
    />
  );
}
