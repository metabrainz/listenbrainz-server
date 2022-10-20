import React, { useState, useCallback, useContext } from "react";
import * as ReactDOM from "react-dom";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { uniqBy } from "lodash";
import Spinner from "react-loader-spinner";
import { withAlertNotifications } from "../notifications/AlertNotificationsHOC";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";

import { getPageProps } from "../utils/utils";
import ErrorBoundary from "../utils/ErrorBoundary";
import ReleaseCard from "./ReleaseCard";
import ReleaseFilters from "./ReleaseFilters";
import ReleaseTimeline from "./ReleaseTimeline";

type FreshReleasesProps = {
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

export default function FreshReleases({ newAlert }: FreshReleasesProps) {
  const { APIService } = useContext(GlobalAppContext);

  const [releases, setReleases] = useState<Array<FreshReleaseItem>>([]);
  const [filteredList, setFilteredList] = useState<Array<FreshReleaseItem>>([]);
  const [allFilters, setAllFilters] = useState<Array<string>>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const fetchReleases = useCallback(async () => {
    setIsLoading(true);
    try {
      const freshReleases: Array<FreshReleaseItem> = await APIService.fetchFreshReleases(
        "",
        2
      );
      const cleanReleases = uniqBy(freshReleases, (datum) => {
        return (
          /*
           * toLowerCase() solves an edge case.
           * Example:
           * "release_name": "Waterslide, Diving Board, Ladder to the Sky"
           * "release_name": "Waterslide, Diving Board, Ladder To The Sky"
           * These releases will be considered unique.
           */
          datum.release_name.toLowerCase() +
          datum.artist_credit_name.toLowerCase()
        );
      });
      const releaseTypes = cleanReleases
        .map(
          (release) =>
            release.release_group_secondary_type ||
            release.release_group_primary_type
        )
        .filter(
          (value, index, self) =>
            self.indexOf(value) === index && value !== undefined
        );

      setReleases(cleanReleases);
      setFilteredList(cleanReleases);
      setAllFilters(releaseTypes);
      setIsLoading(false);
    } catch (error) {
      newAlert("danger", "Couldn't fetch fresh releases", error.toString());
    }
  }, []);

  React.useEffect(() => {
    fetchReleases();
  }, [fetchReleases]);

  return (
    <>
      <h3 id="row">Fresh releases</h3>
      <div className="releases-page row">
        {isLoading ? (
          <div className="spinner-container">
            <Spinner
              type="Grid"
              color="#eb743b"
              height={100}
              width={100}
              visible
            />
            <div
              className="text-muted"
              style={{ fontSize: "2rem", margin: "1rem" }}
            >
              Loading Fresh Releases&#8230;
            </div>
          </div>
        ) : (
          <>
            <div className="filters-main col-xs-12 col-md-1">
              <ReleaseFilters
                allFilters={allFilters}
                releases={releases}
                setFilteredList={setFilteredList}
              />
            </div>
            <div className="release-cards-grid col-xs-9 col-md-10">
              {filteredList?.map((release) => {
                return (
                  <ReleaseCard
                    key={release.release_mbid}
                    releaseDate={release.release_date}
                    releaseMBID={release.release_mbid}
                    releaseName={release.release_name}
                    releaseTypePrimary={release.release_group_primary_type}
                    releaseTypeSecondary={release.release_group_secondary_type}
                    artistCreditName={release.artist_credit_name}
                    artistMBIDs={release.artist_mbids}
                  />
                );
              })}
            </div>
            <div className="releases-timeline col-xs-3 col-md-1">
              {releases.length > 0 ? (
                <ReleaseTimeline releases={releases} />
              ) : null}
            </div>
          </>
        )}
      </div>
    </>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, globalReactProps } = getPageProps();
  const {
    api_url,
    sentry_dsn,
    current_user,
    spotify,
    youtube,
    sentry_traces_sample_rate,
  } = globalReactProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const FreshReleasesPageWithAlertNotifications = withAlertNotifications(
    FreshReleases
  );

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <FreshReleasesPageWithAlertNotifications />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
