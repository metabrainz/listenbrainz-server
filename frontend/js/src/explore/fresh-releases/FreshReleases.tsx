import * as React from "react";
import * as ReactDOM from "react-dom";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { uniqBy } from "lodash";
import Spinner from "react-loader-spinner";
import { withAlertNotifications } from "../../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../../utils/GlobalAppContext";

import { getPageProps } from "../../utils/utils";
import ErrorBoundary from "../../utils/ErrorBoundary";
import ReleaseCard from "./ReleaseCard";
import ReleaseFilters from "./ReleaseFilters";
import ReleaseTimeline from "./ReleaseTimeline";
import Pill from "../../components/Pill";

export type FreshReleasesProps = {
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

export default function FreshReleases({ newAlert }: FreshReleasesProps) {
  const { APIService, currentUser } = React.useContext(GlobalAppContext);

  const isLoggedIn: boolean = Object.keys(currentUser).length !== 0;
  const PAGE_TYPE_USER: string = "user";
  const PAGE_TYPE_SITEWIDE: string = "sitewide";

  const [releases, setReleases] = React.useState<Array<FreshReleaseItem>>([]);
  const [filteredList, setFilteredList] = React.useState<
    Array<FreshReleaseItem>
  >([]);
  const [allFilters, setAllFilters] = React.useState<Array<string | undefined>>(
    []
  );
  const [isLoading, setIsLoading] = React.useState<boolean>(false);
  const [pageType, setPageType] = React.useState<string>(PAGE_TYPE_SITEWIDE);

  React.useEffect(() => {
    const fetchReleases = async () => {
      setIsLoading(true);
      let freshReleases: Array<FreshReleaseItem>;
      try {
        if (pageType === PAGE_TYPE_SITEWIDE) {
          freshReleases = await APIService.fetchSitewideFreshReleases(3);
        } else {
          const userFreshReleases = await APIService.fetchUserFreshReleases(
            currentUser.name
          );
          freshReleases = userFreshReleases.payload.releases;
        }

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
              self.indexOf(value) === index &&
              value !== undefined &&
              value !== null
          );

        setReleases(cleanReleases);
        setFilteredList(cleanReleases);
        setAllFilters(releaseTypes);
        setIsLoading(false);
      } catch (error) {
        newAlert("danger", "Couldn't fetch fresh releases", error.toString());
      }
    };
    // Call the async function defined above (useEffect can't return a Promise)
    fetchReleases();
  }, [pageType]);

  return (
    <>
      <h2 id="fr-heading">Fresh Releases</h2>
      {isLoggedIn ? (
        <>
          <h3 id="fr-subheading">
            Discover new music from artists you listen to
          </h3>
          <div id="fr-pill-row">
            <Pill
              id="sitewide-releases"
              onClick={() => setPageType(PAGE_TYPE_SITEWIDE)}
              active={pageType === PAGE_TYPE_SITEWIDE}
            >
              All Releases
            </Pill>
            <Pill
              id="user-releases"
              onClick={() => setPageType(PAGE_TYPE_USER)}
              active={pageType === PAGE_TYPE_USER}
            >
              Releases For You
            </Pill>
          </div>
        </>
      ) : (
        <h3 id="fr-subheading">Discover new music</h3>
      )}
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
            <div
              id="release-cards-grid"
              className={
                pageType === PAGE_TYPE_SITEWIDE
                  ? "col-xs-12 col-md-10"
                  : "col-xs-12 col-md-11"
              }
            >
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
                    confidence={release.confidence}
                    caaID={release.caa_id}
                    caaReleaseMBID={release.caa_release_mbid}
                  />
                );
              })}
            </div>

            {pageType === PAGE_TYPE_SITEWIDE ? (
              <div className="releases-timeline col-xs-12 col-md-1">
                {releases.length > 0 ? (
                  <ReleaseTimeline releases={filteredList} />
                ) : null}
              </div>
            ) : null}
          </>
        )}
      </div>
    </>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    globalAppContext,
    sentryProps,
    optionalAlerts,
  } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

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

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <FreshReleasesPageWithAlertNotifications
          initialAlerts={optionalAlerts}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
