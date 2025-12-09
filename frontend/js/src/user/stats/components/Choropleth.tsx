import { Theme } from "@nivo/core";
import {
  ResponsiveChoropleth,
  ChoroplethBoundFeature,
  ChoroplethEventHandler,
} from "@nivo/geo";
import { toast } from "react-toastify";
import { BoxLegendSvg, LegendProps } from "@nivo/legends";
import { Chip } from "@nivo/tooltip";
import { scaleThreshold } from "d3-scale";
import { schemeOranges } from "d3-scale-chromatic";
import { format } from "d3-format";
import { debounce, isFinite, isUndefined, maxBy } from "lodash";
import * as React from "react";
import { useMediaQuery } from "react-responsive";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faHeadphones, faPlayCircle } from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";
import * as worldCountries from "../data/world_countries.json";
import { COLOR_BLACK } from "../../../utils/constants";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import enrichJSPFTracks from "../../../utils/Playlist";
import { ToastMsg } from "../../../notifications/Notifications";

const {
  useState,
  useCallback,
  useMemo,
  useEffect,
  useRef,
  useLayoutEffect,
} = React;

export type ChoroplethProps = {
  data: UserArtistMapData;
  selectedMetric: "artist" | "listen";
  colorScaleRange?: string[];
};

const commonLegendProps = {
  anchor: "bottom-left",
  direction: "column",
  itemDirection: "left-to-right",
  itemOpacity: 0.85,
  itemWidth: 90,
  effects: [
    {
      on: "hover",
      style: {
        itemTextColor: COLOR_BLACK,
        itemOpacity: 1,
      },
    },
  ],
};

const legends = {
  desktop: {
    itemHeight: 18,
    symbolSize: 18,
    translateX: 50,
    translateY: -50,
    ...commonLegendProps,
  } as LegendProps,
  mobile: {
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

const tooltipWidth = 250;

export default function CustomChoropleth(props: ChoroplethProps) {
  const [tooltipPosition, setTooltipPosition] = useState([0, 0]);
  const [selectedCountry, setSelectedCountry] = useState<CountryFeature>();
  const refContainer = useRef<HTMLDivElement>(null);
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const tooltipRef = useRef<HTMLButtonElement>(null);

  // Use default container width of 1000px, but promptly calculate the real width in a useLayoutEffect
  const [containerWidth, setContainerWidth] = useState<number>(1000);
  useLayoutEffect(() => {
    // Set the container width *before* initial render
    const width = refContainer.current?.getBoundingClientRect().width;
    if (!isUndefined(width) && isFinite(width)) {
      setContainerWidth(width);
    }

    // Then observe the target element and update the width when resized (with debounce)
    const resizeHandler = (entries: ResizeObserverEntry[]) => {
      // We only observe one element
      const newWidth = entries[0]?.contentBoxSize?.[0].inlineSize;
      setContainerWidth(newWidth);
    };
    const debouncedResizeHandler = debounce(resizeHandler, 1000, {
      leading: false,
      trailing: true,
    });
    let resizeObserver: ResizeObserver | undefined;
    if (refContainer.current && window.ResizeObserver) {
      resizeObserver = new window.ResizeObserver(debouncedResizeHandler);
      resizeObserver.observe(refContainer.current);
    }

    return () => {
      resizeObserver?.disconnect?.();
      debouncedResizeHandler.cancel();
    };
  }, []);

  const isMobile = useMediaQuery({ maxWidth: 767 });

  const { data, colorScaleRange, selectedMetric } = props;

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
    .range(colorScaleRange ?? schemeOranges[6]);

  // Create a custom legend component because the default doesn't work with scaleThreshold
  const customLegend = () => (
    <BoxLegendSvg
      containerHeight={containerWidth / 2}
      containerWidth={containerWidth}
      data={colorScale.range().map((color: string, index: number) => {
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

  const handlePlayCountryTracks = useCallback(
    async (countryName: string) => {
      if (!currentUser?.auth_token) {
        toast.warning(
          <ToastMsg
            title="Please log in"
            message={
              <>
                You must be <Link to="/login">logged in</Link> to use LB Radio.
              </>
            }
          />,
          {
            toastId: "error",
          }
        );
        return;
      }
      try {
        const { payload } = await APIService.getLBRadioPlaylist(
          currentUser.auth_token,
          `country:(${countryName})`
        );
        const tracks = payload.jspf.playlist.track;
        if (!tracks?.length) return;

        const enriched = await enrichJSPFTracks(tracks, APIService);
        window.postMessage(
          { brainzplayer_event: "play-ambient-queue", payload: enriched },
          window.location.origin
        );
      } catch (error) {
        toast.error(<ToastMsg title="Error" message={error.message} />, {
          toastId: "error",
        });
      }
    },
    [APIService, currentUser]
  );

  const customTooltip = useMemo(() => {
    if (!selectedCountry) {
      return null;
    }

    const countryName =
      selectedCountry.properties?.name || selectedCountry.label;
    const countryData = selectedCountry.data ?? { value: 0, artists: [] };
    const { value, artists } = countryData;

    let suffix = `${selectedMetric[0].toUpperCase()}${selectedMetric.slice(1)}`;
    if (Number(selectedCountry.formattedValue) !== 1) {
      suffix = `${suffix}s`;
    }

    return (
      <button
        ref={tooltipRef}
        type="button"
        style={{
          background: "white",
          color: "inherit",
          fontSize: "inherit",
          borderRadius: "2px",
          boxShadow: "0 1px 2px rgba(0, 0, 0, 0.25)",
          maxWidth: `${tooltipWidth}px`,
          width: "100%",
          textAlign: "left",
          padding: 0,
          border: "none",
          cursor: "default",
        }}
        aria-label={`Country details for ${countryName}`}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setSelectedCountry(undefined);
          }
        }}
      >
        <div
          style={{
            padding: "8px 12px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: `linear-gradient(180deg,rgba(252, 252, 252, 1) 0%, rgba(209, 209, 209, 1) 100%)`,
            gap: "8px",
          }}
        >
          <div style={{ fontWeight: "bold", fontSize: "16px" }}>
            {countryName}
          </div>
          <button
            type="button"
            className="btn btn-info btn-rounded btn-sm"
            title={`Play tracks from ${countryName}`}
            style={{
              borderRadius: "50%",
              width: "30px",
              height: "30px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              border: "none",
              cursor: "pointer",
              background: "#353070",
              color: "white",
            }}
            onClick={(e) => {
              e.stopPropagation();
              handlePlayCountryTracks(countryName);
            }}
          >
            <FontAwesomeIcon icon={faPlayCircle as IconProp} />
          </button>
        </div>
        {artists?.length > 0 && (
          <div style={{ padding: "8px 12px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
              }}
            >
              <Chip color={selectedCountry.color!} style={{ marginRight: 7 }} />
              <span>
                Listens:&nbsp;
                <strong>
                  {selectedCountry.formattedValue} {suffix}
                </strong>
              </span>
            </div>

            <hr style={{ margin: "0.5em 0" }} />
            <div
              style={{
                maxHeight: "200px",
                overflowY: "auto",
                overflowX: "hidden",
              }}
            >
              {artists?.map((artist: UserArtistMapArtist) => (
                <div key={artist.artist_mbid}>
                  <span
                    className="badge bg-light text-info"
                    style={{ marginRight: "4px" }}
                  >
                    <FontAwesomeIcon
                      style={{ marginRight: "4px" }}
                      icon={faHeadphones as IconProp}
                    />
                    {new Intl.NumberFormat().format(artist.listen_count)}
                  </span>
                  <Link to={`/artist/${artist.artist_mbid}/`}>
                    {artist.artist_name}
                  </Link>
                  <br />
                </div>
              ))}
            </div>
          </div>
        )}
      </button>
    );
  }, [selectedCountry, selectedMetric, handlePlayCountryTracks]);

  // Hide our custom tooltip when user clicks somewhere that isn't a country
  const handleClickOutside = useCallback(
    (event: MouseEvent) => {
      if (
        tooltipRef.current &&
        tooltipRef.current.contains(event.target as Node)
      ) {
        return; // Don't hide if clicking inside tooltip
      }
      setSelectedCountry(undefined);
    },
    [setSelectedCountry]
  );

  useEffect(() => {
    document.addEventListener("click", handleClickOutside, true);
    return () => {
      document.removeEventListener("click", handleClickOutside, true);
    };
  });

  const showTooltipFromEvent: ChoroplethEventHandler = useCallback(
    (feature: CountryFeature, event: React.MouseEvent<HTMLElement>) => {
      // Cancel other events, such as our handleClickOutside defined above
      event.preventDefault();
      // relative mouse position
      let x = event.clientX;
      let y = event.clientY;
      if (refContainer.current) {
        // Make position relative to parent container
        const bounds = refContainer.current.getBoundingClientRect();
        x -= bounds.left;
        y -= bounds.top;
        // Show tooltip on the left if there isn't enough space
        if (x > bounds.width - tooltipWidth) x -= tooltipWidth / 2;
      }
      setTooltipPosition([x, y]);
      setSelectedCountry(feature);
    },
    [setSelectedCountry, setTooltipPosition]
  );

  return (
    <div
      ref={refContainer}
      className="stats-full-width-graph user-artist-map"
      data-testid="Choropleth"
    >
      <ResponsiveChoropleth
        data={data}
        features={worldCountries.features}
        margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
        colors={colorScale}
        domain={domain}
        theme={isMobile ? themes.mobile : themes.desktop}
        valueFormat=".2~s"
        // We can't set isInteractive to false (need onClick event)
        // But we don't want to show a tooltip, so this function returns an empty element
        // eslint-disable-next-line
        tooltip={() => <></>}
        onClick={showTooltipFromEvent}
        unknownColor="#efefef"
        label={(feature: CountryFeature) => feature.properties.name}
        projectionScale={containerWidth / 5.5}
        projectionType="naturalEarth1"
        projectionTranslation={[0.5, 0.53]}
        borderWidth={0.5}
        borderColor="#152538"
        // The typescript definition file for Choropleth is incomplete, so disable typescript
        // until it is fixed.
        // @ts-ignore
        layers={["features", customLegend]}
      />
      {selectedCountry && (
        <div
          style={{
            transform: `translate(${tooltipPosition[0]}px, ${tooltipPosition[1]}px)`,
            position: "absolute",
            zIndex: 10,
            top: "0px",
            left: "0px",
          }}
        >
          {customTooltip}
        </div>
      )}
    </div>
  );
}
