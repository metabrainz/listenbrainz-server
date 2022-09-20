import * as React from "react";
import * as ReactDOM from "react-dom";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { uniqBy } from "lodash";
import { withAlertNotifications } from "../notifications/AlertNotificationsHOC";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";

import { getPageProps } from "../utils/utils";
import ErrorBoundary from "../utils/ErrorBoundary";
import ReleaseCard from "./ReleaseCard";
import ReleaseFilters from "./ReleaseFilters";

type FreshReleasesProps = {
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

export default function FreshReleases({ newAlert }: FreshReleasesProps) {
  const RELEASE_TYPE_OTHER = "Other";

  const { APIService } = React.useContext(GlobalAppContext);

  const [releases, setReleases] = React.useState<Array<FreshReleaseItem>>();
  const [typesList, setTypesList] = React.useState<Array<string | null>>([]);

  const fetchReleases = React.useCallback(async () => {
    try {
      const freshReleases: Array<FreshReleaseItem> = await APIService.fetchFreshReleases(
        "",
        1
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
            (release.release_group_primary_type ||
              release.release_group_secondary_type) ??
            RELEASE_TYPE_OTHER
        )
        .filter((value, index, self) => self.indexOf(value) === index);

      setReleases(cleanReleases);
      setTypesList(releaseTypes);
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
        <div
          className="col-md-1 hidden-xs hidden-sm hidden-md"
          style={{ padding: "2rem 0" }}
        >
          <ReleaseFilters filters={typesList} />
        </div>
        <div className="release-cards-grid col-xs-12 col-md-10">
          {releases?.map((release) => {
            return (
              <ReleaseCard
                key={release.release_mbid}
                releaseDate={release.release_date}
                releaseMBID={release.release_mbid}
                releaseName={release.release_name}
                releaseType={
                  (release.release_group_primary_type ||
                    release.release_group_secondary_type) ??
                  RELEASE_TYPE_OTHER
                }
                artistCreditName={release.artist_credit_name}
                artistMBIDs={release.artist_mbids}
              />
            );
          })}
        </div>
        <div className="releases-timeline col-xs-12 col-md-1">Timeline</div>
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
