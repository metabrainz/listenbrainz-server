import * as React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCalendar,
  faListAlt,
  faMusic,
} from "@fortawesome/free-solid-svg-icons";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import Pill from "../components/Pill";
import { formatListenCount } from "../explore/fresh-releases/utils";
import Pagination from "../common/Pagination";
import { getObjectForURLSearchParams } from "../utils/utils";
import { RouteQuery } from "../utils/Loader";
import Loader from "../components/Loader";

type DonorLoaderData = {
  data: {
    id: number;
    donated_at: string;
    donation: number;
    currency: "usd" | "eur";
    musicbrainz_id: string;
    is_listenbrainz_user: boolean;
    listenCount: number;
    playlistCount: number;
  }[];
  totalPageCount: number;
};

function Donors() {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsObj = getObjectForURLSearchParams(searchParams);
  const currPageNoStr = searchParams.get("page") || "1";
  const currPageNo = parseInt(currPageNoStr, 10);
  const sort = searchParams.get("sort") || "date";

  const { data, isLoading } = useQuery<DonorLoaderData>(
    RouteQuery(
      ["donors", currPageNoStr, sort],
      `${location.pathname}${location.search}`
    )
  );

  const { data: donors, totalPageCount = 1 } = data || {};

  const handleClickPrevious = () => {
    setSearchParams({
      ...searchParamsObj,
      page: Math.max(currPageNo - 1, 1).toString(),
    });
  };

  const handleClickNext = () => {
    setSearchParams({
      ...searchParamsObj,
      page: Math.min(currPageNo + 1, totalPageCount).toString(),
    });
  };

  const handleSortBy = (sortBy: string) => {
    if (sortBy === sort) {
      return;
    }
    setSearchParams({
      page: "1",
      sort: sortBy,
    });
  };

  return (
    <div role="main" id="donors">
      <div className="listen-header">
        <h2 className="header-with-line">Donations</h2>
        <div className="flex" role="group" aria-label="Sort by">
          <Pill
            type="secondary"
            active={sort === "date"}
            onClick={() => handleSortBy("date")}
          >
            Date
          </Pill>
          <Pill
            type="secondary"
            active={sort === "amount"}
            onClick={() => handleSortBy("amount")}
          >
            Amount
          </Pill>
        </div>
      </div>
      <Loader isLoading={isLoading}>
        {donors?.map((donor) => (
          <div key={donor.id} className="donor-card">
            <div className="donor-info">
              <div className="donation-user">
                {donor.musicbrainz_id &&
                  (donor.is_listenbrainz_user ? (
                    <Link
                      to={`/user/${donor.musicbrainz_id}`}
                      className="donor-name"
                    >
                      {donor.musicbrainz_id}
                    </Link>
                  ) : (
                    <Link
                      to={`https://musicbrainz.org/user/${donor.musicbrainz_id}`}
                      className="donor-name"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {donor.musicbrainz_id}
                    </Link>
                  ))}
              </div>
              <div className="donation-date">
                <FontAwesomeIcon icon={faCalendar} />
                <span>
                  Donation Date:{" "}
                  {new Date(donor.donated_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            <div className="donor-stats">
              <p className="donation-amount">
                {donor.currency === "usd" ? "$" : "€"}
                {donor.donation}
              </p>
              {donor.musicbrainz_id && donor.is_listenbrainz_user ? (
                <div className="recent-listens">
                  {donor.listenCount ? (
                    <Link
                      className="listen-item"
                      to={`/user/${donor.musicbrainz_id}/stats/?range=all_time`}
                    >
                      <FontAwesomeIcon icon={faMusic} />
                      {formatListenCount(donor.listenCount)} Listens
                    </Link>
                  ) : null}
                  {donor.playlistCount ? (
                    <Link
                      className="listen-item"
                      to={`/user/${donor.musicbrainz_id}/playlists/`}
                    >
                      <FontAwesomeIcon icon={faListAlt} />
                      {formatListenCount(donor.playlistCount)} Playlists
                    </Link>
                  ) : null}
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </Loader>
      <Pagination
        currentPageNo={currPageNo}
        totalPageCount={totalPageCount}
        handleClickPrevious={handleClickPrevious}
        handleClickNext={handleClickNext}
      />
    </div>
  );
}

export default Donors;
