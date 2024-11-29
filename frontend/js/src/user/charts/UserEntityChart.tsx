/* eslint-disable jsx-a11y/anchor-is-valid */
import * as React from "react";
import {
  faAngleDoubleLeft,
  faAngleDoubleRight,
  faAngleLeft,
  faAngleRight,
  faExclamationCircle,
  faHeadphones,
  faRss,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { useLoaderData, Link, useNavigate, json } from "react-router-dom";
import { Helmet } from "react-helmet";
import { BarItemProps } from "@nivo/bar";
import NiceModal from "@ebay/nice-modal-react";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getData, processData } from "./utils";

import Bar from "./components/Bar";
import Loader from "../../components/Loader";
import Pill from "../../components/Pill";
import {
  getAllStatRanges,
  getChartEntityDetails,
  getEntityLink,
  isInvalidStatRange,
  userChartEntityToListen,
} from "../stats/utils";
import ListenCard from "../../common/listens/ListenCard";
import { useBrainzPlayerDispatch } from "../../common/brainzplayer/BrainzPlayerContext";
import { COLOR_LB_ASPHALT, COLOR_LB_ORANGE } from "../../utils/constants";
import { getBaseUrl, getStatsArtistLink } from "../../utils/utils";
import { useMediaQuery } from "../../explore/fresh-releases/utils";
import ReleaseCard from "../../explore/fresh-releases/components/ReleaseCard";
import SyndicationFeedModal from "../../components/SyndicationFeedModal";

export type UserEntityChartProps = {
  user?: ListenBrainzUser;
  entity: Entity;
  terminology: "artist" | "album" | "track";
  range: UserStatsAPIRange;
  currPage: number;
};

type UserEntityChartLoaderData = UserEntityChartProps;

export const TERMINOLOGY_ENTITY_MAP: Record<string, Entity> = {
  artist: "artist",
  album: "release-group",
  track: "recording",
};

const ROWS_PER_PAGE = 25;

// @ts-ignore - Not sure why it does not accept UserEntityDatum,
// but BarDatum does not represent the actual data format we have.
function CustomBarComponent(barProps: BarItemProps<UserEntityDatum>) {
  const { bar } = barProps;
  const { x, y, width, height, data } = bar;
  let title = `#${data.data.idx} (${data.data.count} listen${
    data.data.count === 1 ? "" : "s"
  }) | ${data.data.entity}`;
  if (data.data.artist) {
    title += ` - ${data.data.artist}`;
  }

  return (
    <g transform={`translate(${x}, ${y})`}>
      <rect
        width={width}
        height={height}
        fill={data.fill}
        strokeWidth="0"
        rx="0"
      />
      <foreignObject style={{ width: Math.max(170, width), height }}>
        <div className="graph-bar flex" title={title}>
          <div className="position">
            {data.data.count}
            <br />
            <FontAwesomeIcon icon={faHeadphones} />
          </div>
          <div className="graph-bar-text">
            <div className="graph-bar-entity ellipsis-2-lines">
              {getEntityLink(
                data.data.entityType,
                data.data.entity,
                data.data.entityMBID
              )}
            </div>
            {data.data.artist && (
              <div className="graph-bar-artist ellipsis">
                {getStatsArtistLink(
                  data.data.artists,
                  data.data.artist,
                  data.data.artistMBID
                )}
              </div>
            )}
          </div>
        </div>
      </foreignObject>
    </g>
  );
}

export default function UserEntityChart() {
  const loaderData = useLoaderData() as UserEntityChartLoaderData;
  const { user, entity, terminology, range, currPage } = loaderData;
  const prevPage = currPage - 1;
  const nextPage = currPage + 1;

  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const navigate = useNavigate();

  const [loading, setLoading] = React.useState(true);
  const [hasError, setHasError] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState("");

  const [data, setData] = React.useState<UserEntityData>([]);
  const [maxListens, setMaxListens] = React.useState(0);
  const [totalPages, setTotalPages] = React.useState(0);
  const [entityCount, setEntityCount] = React.useState(0);
  const [startDate, setStartDate] = React.useState<Date | undefined>(undefined);
  const [endDate, setEndDate] = React.useState<Date | undefined>(undefined);
  const ranges = getAllStatRanges();

  const isMobile = useMediaQuery("(max-width: 767px)");

  React.useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setHasError(false);

      if (isInvalidStatRange(range)) {
        navigate(window.location.pathname);
        return;
      }

      try {
        const fetchedData = await getData(
          APIService,
          entity,
          currPage,
          range,
          ROWS_PER_PAGE,
          user
        );
        const entityData = processData(
          fetchedData.entityData,
          currPage,
          entity,
          ROWS_PER_PAGE
        );
        setData(entityData);
        setMaxListens(fetchedData.maxListens);
        setTotalPages(fetchedData.totalPages);
        setEntityCount(fetchedData.entityCount);
        setStartDate(fetchedData.startDate);
        setEndDate(fetchedData.endDate);
      } catch (error) {
        setHasError(true);
        setErrorMessage(error.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [APIService, currPage, entity, range, user, loaderData, navigate]);

  const listenableItems: BaseListenFormat[] =
    data?.map(userChartEntityToListen) ?? [];

  const dispatch = useBrainzPlayerDispatch();

  React.useEffect(() => {
    // If the entity is an artist or recording, then we add the release name or release group name to the track name for the listen so that BrainzPlayer plays a track from the release or release group.
    if (["release", "release-group"].includes(entity)) {
      const listensToDispatch = listenableItems.map((listen) => {
        const releaseName = listen.track_metadata?.release_name;
        const releaseGroupName =
          listen.track_metadata?.mbid_mapping?.release_group_name;
        return {
          ...listen,
          track_metadata: {
            ...listen.track_metadata,
            track_name: releaseName || releaseGroupName || "",
          },
        };
      });
      dispatch({
        type: "SET_AMBIENT_QUEUE",
        data: listensToDispatch,
      });
      return;
    }

    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: listenableItems,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listenableItems]);

  const userOrLoggedInUser: string | undefined =
    user?.name ?? currentUser?.name;

  const userStatsTitle =
    user?.name === currentUser?.name ? "Your" : `${userOrLoggedInUser}'s`;

  const attributesForLinks = `?range=${range}`;
  return (
    <div role="main">
      <Helmet>
        <title>
          {user?.name ? userStatsTitle : "Sitewide"} top {terminology}s
        </title>
      </Helmet>
      <div style={{ marginTop: "1em", minHeight: 500 }}>
        <Loader isLoading={loading}>
          <div>
            <Pill active={terminology === "artist"} type="secondary">
              <Link
                to={`../top-artists/${attributesForLinks}`}
                relative="route"
                className="user-charts-pill"
              >
                Artists
              </Link>
            </Pill>
            <Pill active={terminology === "album"} type="secondary">
              <Link
                to={`../top-albums/${attributesForLinks}`}
                relative="route"
                className="user-charts-pill"
              >
                Albums
              </Link>
            </Pill>
            <Pill active={terminology === "track"} type="secondary">
              <Link
                to={`../top-tracks/${attributesForLinks}`}
                relative="route"
                className="user-charts-pill"
              >
                Tracks
              </Link>
            </Pill>
          </div>
          <div className="flex-center">
            <h3 className="header-with-line">
              <span>
                Top{" "}
                <span style={{ textTransform: "capitalize" }}>
                  {terminology ? `${terminology}s` : ""}
                </span>{" "}
                of {range !== "all_time" ? "the" : ""}
                <span className="dropdown" style={{ fontSize: 22 }}>
                  <button
                    className="dropdown-toggle btn-transparent capitalize-bold"
                    data-toggle="dropdown"
                    type="button"
                  >
                    {ranges.get(range)}
                    <span className="caret" />
                  </button>
                  <ul className="dropdown-menu" role="menu">
                    {Array.from(ranges, ([stat_type, stat_name]) => {
                      return (
                        <li key={`${stat_type}-${stat_name}`}>
                          <Link
                            to={{
                              pathname: window.location.pathname,
                              search: `?page=1&range=${stat_type}`,
                            }}
                            role="button"
                          >
                            {stat_name}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                </span>
                {range !== "all_time" &&
                  !hasError &&
                  `(${startDate?.toLocaleString("en-us", {
                    day: "2-digit",
                    month: "long",
                    year: "numeric",
                  })} - ${endDate?.toLocaleString("en-us", {
                    day: "2-digit",
                    month: "long",
                    year: "numeric",
                  })})`}
              </span>
            </h3>
            {Boolean(user?.name) && (
              <button
                type="button"
                className="btn btn-icon btn-info atom-button"
                style={{ marginLeft: "auto" }}
                data-toggle="modal"
                data-target="#SyndicationFeedModal"
                title="Subscribe to syndication feed (Atom)"
                onClick={() => {
                  NiceModal.show(SyndicationFeedModal, {
                    feedTitle: `Top ${terminology}s`,
                    options: [
                      {
                        label: "Time range",
                        tooltip:
                          "Select the time range for the feed. For instance, choosing 'this week' will include listens from the current week. It's recommended to set your feed reader's refresh interval to match this time range for optimal updates.",
                        key: "range",
                        type: "dropdown",
                        values: Array.from(
                          ranges,
                          ([stat_type, stat_name]) => ({
                            id: stat_type,
                            value: stat_type,
                            displayValue: stat_name,
                          })
                        ),
                      },
                      {
                        label: "Count",
                        key: "count",
                        type: "number",
                        defaultValue: 10,
                        min: 1,
                      },
                    ],
                    baseUrl: `${getBaseUrl()}/syndication-feed/user/${
                      user?.name
                    }/stats/top-${terminology}s`,
                  });
                }}
              >
                <FontAwesomeIcon icon={faRss} size="sm" />
              </button>
            )}
          </div>
          {hasError && (
            <div className="mt-15 mb-15">
              <div className="text-center">
                <span style={{ fontSize: 24 }}>
                  <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
                  {errorMessage}
                </span>
              </div>
            </div>
          )}
          {!hasError && (
            <>
              {entityCount && (
                <h4>
                  <span style={{ textTransform: "capitalize" }}>
                    {terminology}
                  </span>
                  &nbsp;count - <b>{entityCount} total</b>
                  {entityCount > 1000 && (
                    <span className="small">
                      &nbsp;(showing the first 1000)
                    </span>
                  )}
                </h4>
              )}
              <div
                className="row bar-chart"
                style={{
                  minHeight: `calc(${Math.min(data.length, 25)} * 4.5em)`,
                }}
              >
                <Bar
                  isMobileSize={isMobile}
                  data={[...data].reverse()}
                  isInteractive={false}
                  maxValue={maxListens}
                  layout="horizontal"
                  barComponent={CustomBarComponent}
                  labelTextColor={COLOR_LB_ASPHALT}
                  margin={{
                    bottom: 40,
                    top: 40,
                    left: isMobile ? 5 : 15,
                    right: isMobile ? 30 : 15,
                  }}
                  defs={[
                    {
                      id: "barGradient",
                      type: "linearGradient",
                      colors: [
                        {
                          offset: 10,
                          color: "antiquewhite",
                        },
                        {
                          offset: 90,
                          color: COLOR_LB_ORANGE,
                        },
                      ],
                      y2: "90vw",
                      gradientTransform: "rotate(-90)",
                      gradientUnits: "userSpaceOnUse",
                    },
                  ]}
                  fill={[{ match: "*", id: "barGradient" }]}
                  // labelPosition="start" // Upcoming nivo release, see https://github.com/plouc/nivo/pull/2585
                />
              </div>
              {totalPages > 1 && (
                <div className="text-center">
                  <ul className="pagination">
                    <li
                      className={`previous ${
                        !(prevPage > 0) ? "disabled" : ""
                      }`}
                      title="First page"
                    >
                      <Link
                        to={{
                          pathname: window.location.pathname,
                          search: `?page=1&range=${range}`,
                        }}
                        role="button"
                      >
                        <FontAwesomeIcon
                          icon={faAngleDoubleLeft}
                          size="sm"
                          style={{ verticalAlign: "middle" }}
                        />
                      </Link>
                    </li>
                    <li
                      className={`previous ${
                        !(prevPage > 0) ? "disabled" : ""
                      }`}
                      title="Previous page"
                    >
                      <Link
                        to={{
                          pathname: window.location.pathname,
                          search: `?page=${prevPage}&range=${range}`,
                        }}
                        role="button"
                      >
                        <FontAwesomeIcon
                          icon={faAngleLeft}
                          size="sm"
                          style={{ verticalAlign: "middle" }}
                        />{" "}
                        Previous
                      </Link>
                    </li>
                    {currPage > 3 && (
                      <li>
                        <span>...</span>
                      </li>
                    )}
                    {currPage > 2 && currPage - 2 < totalPages && (
                      <li>
                        <Link
                          to={{
                            pathname: window.location.pathname,
                            search: `?page=${currPage - 2}&range=${range}`,
                          }}
                          role="button"
                        >
                          {currPage - 2}
                        </Link>
                      </li>
                    )}
                    {currPage > 1 && currPage - 1 < totalPages && (
                      <li>
                        <Link
                          to={{
                            pathname: window.location.pathname,
                            search: `?page=${currPage - 1}&range=${range}`,
                          }}
                          role="button"
                        >
                          {currPage - 1}
                        </Link>
                      </li>
                    )}
                    <li title="Current page" className="active">
                      <span>page {currPage}</span>
                    </li>
                    {currPage + 1 <= totalPages && (
                      <li>
                        <Link
                          to={{
                            pathname: window.location.pathname,
                            search: `?page=${currPage + 1}&range=${range}`,
                          }}
                          role="button"
                        >
                          {currPage + 1}
                        </Link>
                      </li>
                    )}
                    {currPage + 2 <= totalPages && (
                      <li>
                        <Link
                          to={{
                            pathname: window.location.pathname,
                            search: `?page=${currPage + 2}&range=${range}`,
                          }}
                          role="button"
                        >
                          {currPage + 2}
                        </Link>
                      </li>
                    )}
                    {currPage + 2 < totalPages && (
                      <li>
                        <span>...</span>
                      </li>
                    )}
                    <li
                      className={`next ${
                        !(nextPage <= totalPages) ? "disabled" : ""
                      }`}
                      title="Next page"
                    >
                      <Link
                        to={{
                          pathname: window.location.pathname,
                          search: `?page=${nextPage}&range=${range}`,
                        }}
                        role="button"
                      >
                        Next{" "}
                        <FontAwesomeIcon
                          icon={faAngleRight}
                          size="sm"
                          style={{ verticalAlign: "middle" }}
                        />
                      </Link>
                    </li>
                    <li
                      className={`next ${
                        !(nextPage <= totalPages) ? "disabled" : ""
                      }`}
                      title="Last page"
                    >
                      <Link
                        to={{
                          pathname: window.location.pathname,
                          search: `?page=${totalPages}&range=${range}`,
                        }}
                        role="button"
                      >
                        <FontAwesomeIcon
                          icon={faAngleDoubleRight}
                          size="sm"
                          style={{ verticalAlign: "middle" }}
                        />
                      </Link>
                    </li>
                  </ul>
                </div>
              )}

              {(entity === "artist" || entity === "recording") && (
                <div className="top-entity-listencards">
                  {data?.slice().map((datum, index) => {
                    const listen = listenableItems[index];
                    const listenDetails = getChartEntityDetails(datum);
                    const listenCountComponent = (
                      <span className="badge badge-info">
                        {datum.count}
                        &nbsp;
                        <FontAwesomeIcon icon={faHeadphones} />
                      </span>
                    );
                    return (
                      <ListenCard
                        key={`${datum.idx + 1}`}
                        listenDetails={listenDetails}
                        listen={listen}
                        showTimestamp={false}
                        showUsername={false}
                        additionalActions={listenCountComponent}
                      />
                    );
                  })}
                </div>
              )}

              {(entity === "release" || entity === "release-group") && (
                <>
                  <p className="small">
                    <sup>*</sup>The listen count denotes the number of times you
                    have listened to a recording from the release group.
                  </p>
                  <div className="release-cards-grid top-entity-grid">
                    {data?.slice().map((datum, index) => {
                      return (
                        <ReleaseCard
                          key={datum.entity + datum.entityMBID}
                          releaseName={datum.entity}
                          releaseGroupMBID={
                            entity === "release-group"
                              ? datum.entityMBID
                              : datum.releaseGroupMBID
                          }
                          releaseMBID={datum.releaseMBID}
                          artistMBIDs={
                            datum.artistMBID ??
                            datum.artists?.map((a) => a.artist_mbid) ??
                            []
                          }
                          artistCredits={datum.artists}
                          artistCreditName={datum.artist as string}
                          listenCount={datum.count}
                          caaID={datum.caaID ?? null}
                          caaReleaseMBID={datum.caaReleaseMBID ?? null}
                          showListens
                          showReleaseTitle
                          showArtist
                        />
                      );
                    })}
                  </div>
                </>
              )}
            </>
          )}
        </Loader>
      </div>
    </div>
  );
}

export const UserEntityChartLoader = async ({
  request,
}: {
  request: Request;
}) => {
  const currentURL = new URL(request.url);
  const response = await fetch(currentURL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });
  const propsData = await response.json();
  if (!response.ok) {
    throw json(propsData, { status: response.status });
  }
  const { user } = propsData;

  const page = Math.max(Number(currentURL.searchParams.get("page")), 1);
  const range: UserStatsAPIRange =
    (currentURL.searchParams.get("range") as UserStatsAPIRange) ?? "all_time";

  const match = currentURL.pathname.match(
    /\/user\/.+\/stats\/top-(artist|album|track)s/
  );
  const urlEntityName = match?.[1] ?? "artist";
  const entity = TERMINOLOGY_ENTITY_MAP[urlEntityName];

  return {
    user,
    entity,
    terminology: urlEntityName,
    currPage: page,
    range,
  };
};

export const StatisticsChartLoader = async ({
  request,
}: {
  request: Request;
}) => {
  const currentURL = new URL(request.url);
  const page = Math.max(Number(currentURL.searchParams.get("page")), 1);
  const range: UserStatsAPIRange =
    (currentURL.searchParams.get("range") as UserStatsAPIRange) ?? "all_time";

  const match = currentURL.pathname.match(
    /\/statistics\/top-(artist|album|track)s/
  );
  const urlEntityName = match?.[1] ?? "artist";
  const entity = TERMINOLOGY_ENTITY_MAP[urlEntityName];

  return {
    user: undefined,
    entity,
    terminology: urlEntityName,
    currPage: page,
    range,
  };
};
