import { ResponsiveBar } from "@nivo/bar";
import * as React from "react";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, Link } from "react-router";
import { useMediaQuery } from "react-responsive";
import Card from "../../../components/Card";
import Loader from "../../../components/Loader";
import GlobalAppContext from "../../../utils/GlobalAppContext";

export type UserArtistActivityProps = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
};

export declare type ChartDataItem = {
  label: string;
  [albumName: string]: number | string;
};

// Define CustomTooltip outside of the main component
function CustomTooltip({
  id,
  value,
  color,
}: {
  id: string;
  value: number;
  color: string;
}) {
  const formattedValue = new Intl.NumberFormat().format(value);
  return (
    <div
      style={{
        padding: "10px",
        background: "white",
        border: `1px solid ${color}`,
        borderRadius: "4px",
        boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
      }}
    >
      <strong>
        {id}: {formattedValue}
      </strong>
    </div>
  );
}

export default function UserArtistActivity(props: UserArtistActivityProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const navigate = useNavigate();
  const isMobile = useMediaQuery({ maxWidth: 767 });

  // Props
  const { user, range } = props;

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["userArtistActivity", user?.name, range],
    queryFn: async () => {
      try {
        const queryData = await APIService.getUserArtistActivity(
          user?.name,
          range
        );
        return { data: queryData, hasError: false, errorMessage: "" };
      } catch (error) {
        return {
          data: { result: [] } as UserArtistActivityResponse,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const {
    data: rawData = { result: [] } as UserArtistActivityResponse,
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const wrapWordsByLength = (str: string, maxLen: number): string => {
    const words = str.split(" ");
    const lines: string[] = [];
    let currentLine = words[0];
    for (let i = 1; i < words.length; i += 1) {
      if (currentLine.length + 1 + words[i].length <= maxLen) {
        currentLine += ` ${words[i]}`;
      } else {
        lines.push(currentLine);
        currentLine = words[i];
      }
    }
    lines.push(currentLine);
    return lines.join("\n");
  };

  const processData = (data?: UserArtistActivityResponse) => {
    if (!data || !data.result || data.result.length === 0) {
      return [];
    }
    return data.result.map((artist) => {
      const wrappedLabel = wrapWordsByLength(artist.name, 14);
      return {
        label: wrappedLabel,
        ...artist.albums.reduce(
          (acc, album) => ({ ...acc, [album.name]: album.listen_count }),
          {} as Record<string, number>
        ),
      };
    }) as ChartDataItem[];
  };
  const [chartData, setChartData] = React.useState<ChartDataItem[]>([]);

  const albumRedirectMapping = React.useMemo(() => {
    const mapping: Record<string, string> = {};
    if (rawData && rawData.result) {
      rawData.result.forEach((artist) => {
        artist.albums.forEach((album) => {
          if (album.release_group_mbid) {
            mapping[`${artist.name}-${album.name}`] = album.release_group_mbid;
          }
        });
      });
    }
    return mapping;
  }, [rawData]);

  React.useEffect(() => {
    if (rawData && rawData.result.length > 0) {
      const processedData = processData(rawData);
      setChartData(processedData);
    }
  }, [rawData]);

  const tooltipRenderer = React.useCallback(
    (tooltipProps: { id: string | number; value: number; color: string }) => {
      const { id, value, color } = tooltipProps;
      return <CustomTooltip id={id as string} value={value} color={color} />;
    },
    []
  );

  return (
    <Card className="user-stats-card" data-testid="user-artist-activity">
      <div className="d-flex align-items-baseline">
        <h3 className="capitalize-bold">Artist Activity</h3>
        <a
          href="#artist-activity"
          className="btn btn-icon btn-link ms-auto text-body fs-3"
        >
          <FontAwesomeIcon icon={faLink as IconProp} />
        </a>
      </div>
      <Loader isLoading={loading}>
        {hasError ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: "inherit",
            }}
          >
            <span style={{ fontSize: 24 }}>
              <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
              {errorMessage}
            </span>
          </div>
        ) : (
          <div className="row">
            <div className="col-xs-12">
              <div
                style={{
                  width: "100%",
                  height: "600px",
                  minHeight: "400px",
                  textAlign: "right",
                  fontSize: "11px",
                  lineHeight: "1em",
                }}
              >
                <ResponsiveBar
                  data={chartData}
                  keys={Array.from(
                    new Set(
                      chartData.flatMap((item) =>
                        Object.keys(item).filter((key) => key !== "label")
                      )
                    )
                  )}
                  indexBy="label"
                  margin={{
                    top: 20,
                    right: isMobile ? 0 : 80,
                    bottom: 100,
                    left: isMobile ? 20 : 120,
                  }}
                  padding={0.2}
                  layout="vertical"
                  colors={{ scheme: "nivo" }}
                  borderColor={{ from: "color", modifiers: [["darker", 1.6]] }}
                  enableLabel={false}
                  axisBottom={{
                    tickSize: 5,
                    tickPadding: 5,
                    tickRotation: -45,
                    renderTick: (tick) => {
                      const artistMbid =
                        rawData?.result?.[tick.tickIndex]?.artist_mbid || "";
                      const artistName =
                        rawData?.result?.[tick.tickIndex]?.name || "";
                      const linkTo = artistMbid
                        ? `/artist/${artistMbid}`
                        : `/search?search_term=${encodeURIComponent(
                            artistName
                          )}&search_type=artist`;
                      return (
                        <g transform={`translate(${tick.x},${tick.y})`}>
                          <foreignObject
                            x="-90"
                            y="0"
                            width="90"
                            height="30"
                            style={{
                              overflow: "visible",
                              transform: "translate(-5px, 5px) rotate(-45deg)",
                            }}
                          >
                            <Link to={linkTo} className="ellipsis-3-lines">
                              {tick.value}
                            </Link>
                          </foreignObject>
                        </g>
                      );
                    },
                  }}
                  onClick={(barData, event) => {
                    const albumName = barData.id;
                    const artistName = barData.indexValue;
                    const releaseGroupMbid =
                      albumRedirectMapping[`${artistName}-${albumName}`];
                    if (releaseGroupMbid) {
                      navigate(`/album/${releaseGroupMbid}`);
                    }
                  }}
                  tooltip={tooltipRenderer}
                />
              </div>
            </div>
          </div>
        )}
      </Loader>
    </Card>
  );
}
