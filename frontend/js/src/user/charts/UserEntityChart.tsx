/* eslint-disable jsx-a11y/anchor-is-valid */
import * as React from "react";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { useLoaderData, Link, useNavigate } from "react-router-dom";
import { Helmet } from "react-helmet";
import GlobalAppContext from "../../utils/GlobalAppContext";
import BrainzPlayer from "../../common/brainzplayer/BrainzPlayer";
import { getInitData, getData, processData } from "./utils";

import Bar from "./components/Bar";
import Loader from "../../components/Loader";
import Pill from "../../components/Pill";
import {
  getAllStatRanges,
  getChartEntityDetails,
  isInvalidStatRange,
  userChartEntityToListen,
} from "../stats/utils";
import ListenCard from "../../common/listens/ListenCard";

export type UserEntityChartProps = {
  user?: ListenBrainzUser;
  entity: Entity;
  terminology: string;
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

export default function UserEntityChart() {
  const loaderData = useLoaderData() as UserEntityChartLoaderData;
  const { user, entity, terminology, range, currPage } = loaderData;
  const prevPage = currPage - 1;
  const nextPage = currPage + 1;

  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const navigate = useNavigate();

  const [loading, setLoading] = React.useState(true);
  const [listenContainerHeight, setListenContainerHeight] = React.useState<
    number | undefined
  >(undefined);
  const [hasError, setHasError] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState("");

  const [data, setData] = React.useState<UserEntityData>([]);
  const [maxListens, setMaxListens] = React.useState(0);
  const [totalPages, setTotalPages] = React.useState(0);
  const [entityCount, setEntityCount] = React.useState(0);
  const [startDate, setStartDate] = React.useState<Date | undefined>(undefined);
  const [endDate, setEndDate] = React.useState<Date | undefined>(undefined);
  const ranges = getAllStatRanges();

  React.useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setHasError(false);

      if (isInvalidStatRange(range)) {
        navigate(window.location.pathname);
        return;
      }

      try {
        const [initData, fetchedData] = await Promise.all([
          getInitData(APIService, entity, range, ROWS_PER_PAGE, user),
          getData(
            APIService,
            entity,
            currPage,
            range,
            ROWS_PER_PAGE,
            user
          ).then((dataFetched) => {
            return processData(dataFetched, currPage, entity, ROWS_PER_PAGE);
          }),
        ]);

        setData(fetchedData);
        setMaxListens(initData.maxListens);
        setTotalPages(initData.totalPages);
        setEntityCount(initData.entityCount);
        setStartDate(initData.startDate);
        setEndDate(initData.endDate);
      } catch (error) {
        setHasError(true);
        setErrorMessage(error.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [APIService, currPage, entity, range, user, loaderData, navigate]);

  const listenContainer = React.useRef<HTMLDivElement>(null);

  const handleResize = () => {
    setListenContainerHeight(listenContainer.current?.offsetHeight);
  };

  React.useEffect(() => {
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  });

  const listenableItems: BaseListenFormat[] =
    data?.map(userChartEntityToListen).reverse() ?? [];

  const userOrLoggedInUser: string | undefined =
    user?.name ?? currentUser?.name;

  const userStatsTitle =
    user?.name === currentUser?.name ? "Your" : `${userOrLoggedInUser}'s`;

  return (
    <div role="main">
      <Helmet>
        <title>
          {user?.name ? userStatsTitle : "Sitewide"} top {terminology}s -
          ListenBrainz
        </title>
      </Helmet>
      <div style={{ marginTop: "1em", minHeight: 500 }}>
        <Loader isLoading={loading}>
          <div className="row">
            <div className="col-xs-12">
              <Pill active={entity === "artist"} type="secondary">
                <Link
                  to="../top-artists/"
                  relative="route"
                  className="user-charts-pill"
                  replace
                >
                  Artists
                </Link>
              </Pill>
              <Pill active={entity === "release-group"} type="secondary">
                <Link
                  to="../top-albums/"
                  relative="route"
                  className="user-charts-pill"
                  replace
                >
                  Albums
                </Link>
              </Pill>
              <Pill active={entity === "recording"} type="secondary">
                <Link
                  to="../top-tracks/"
                  relative="route"
                  className="user-charts-pill"
                  replace
                >
                  Tracks
                </Link>
              </Pill>
            </div>
          </div>
          <div className="row">
            <div className="col-xs-12">
              <h3>
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
              </h3>
            </div>
          </div>
          {hasError && (
            <div className="row mt-15 mb-15">
              <div className="col-xs-12 text-center">
                <span style={{ fontSize: 24 }}>
                  <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
                  {errorMessage}
                </span>
              </div>
            </div>
          )}
          {!hasError && (
            <>
              <div className="row">
                <div className="col-xs-12">
                  <h4 style={{ textTransform: "capitalize" }}>
                    {terminology} count - <b>{entityCount}</b>
                  </h4>
                </div>
              </div>
              <div className="row">
                <div className="col-xs-6" ref={listenContainer}>
                  {data
                    ?.slice()
                    .reverse()
                    .map((datum, index) => {
                      const listen = listenableItems[index];
                      const listenDetails = getChartEntityDetails(datum);
                      return (
                        <ListenCard
                          key={`${datum.idx + 1}`}
                          listenDetails={listenDetails}
                          listen={listen}
                          showTimestamp={false}
                          showUsername={false}
                        />
                      );
                    })}
                </div>
                <div
                  className="col-xs-6"
                  style={{
                    height:
                      listenContainerHeight ?? `${65 * (data?.length ?? 1)}px`,
                    paddingLeft: 0,
                  }}
                >
                  <Bar data={data} maxValue={maxListens} />
                </div>
              </div>
              {entity === "release-group" && (
                <div className="row">
                  <div className="col-xs-12">
                    <small>
                      <sup>*</sup>The listen count denotes the number of times
                      you have listened to a recording from the release group.
                    </small>
                  </div>
                </div>
              )}
              <div className="row">
                <div className="col-xs-12">
                  <ul className="pager">
                    <li
                      className={`previous ${
                        !(prevPage > 0) ? "disabled" : ""
                      }`}
                    >
                      <Link
                        to={{
                          pathname: window.location.pathname,
                          search: `?page=${prevPage}&range=${range}`,
                        }}
                        role="button"
                      >
                        &larr; Previous
                      </Link>
                    </li>
                    <li
                      className={`next ${
                        !(nextPage <= totalPages) ? "disabled" : ""
                      }`}
                    >
                      <Link
                        to={{
                          pathname: window.location.pathname,
                          search: `?page=${nextPage}&range=${range}`,
                        }}
                        role="button"
                      >
                        Next &rarr;
                      </Link>
                    </li>
                  </ul>
                </div>
              </div>
            </>
          )}
        </Loader>
      </div>

      <BrainzPlayer
        listens={listenableItems}
        listenBrainzAPIBaseURI={APIService.APIBaseURI}
        refreshSpotifyToken={APIService.refreshSpotifyToken}
        refreshYoutubeToken={APIService.refreshYoutubeToken}
        refreshSoundcloudToken={APIService.refreshSoundcloudToken}
      />
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
  const { user } = propsData;

  const page = Math.max(Number(currentURL.searchParams.get("page")), 1);
  const range: UserStatsAPIRange =
    (currentURL.searchParams.get("range") as UserStatsAPIRange) ?? "all_time";

  const reg = new RegExp(
    `/user/${user?.name}/stats/top-(artist|album|track)s`,
    "gm"
  );
  const match = reg.exec(currentURL.pathname);
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

  const match = /\/statistics\/top-(artist|album|track)s/gm.exec(
    currentURL.pathname
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
