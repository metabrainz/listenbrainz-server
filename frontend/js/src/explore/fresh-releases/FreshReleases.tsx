import * as React from "react";
import * as Sentry from "@sentry/react";
import { createRoot } from "react-dom/client";
import { Integrations } from "@sentry/tracing";
import { uniqBy } from "lodash";
import Spinner from "react-loader-spinner";
import { toast } from "react-toastify";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { ToastMsg } from "../../notifications/Notifications";
import { getPageProps } from "../../utils/utils";
import ErrorBoundary from "../../utils/ErrorBoundary";
import ReleaseFilters from "./ReleaseFilters";
import ReleaseTimeline from "./ReleaseTimeline";
import Pill from "../../components/Pill";
import ReleaseCardsGrid from "./ReleaseCardsGrid";

export enum DisplaySettingsPropertiesEnum {
  releaseTitle = "Release Title",
  artist = "Artist",
  information = "Information",
  tags = "Tags",
  listens = "Listens",
}

export type DisplaySettings = {
  [key in DisplaySettingsPropertiesEnum]: boolean;
};

const initialDisplayState: DisplaySettings = {
  [DisplaySettingsPropertiesEnum.releaseTitle]: true,
  [DisplaySettingsPropertiesEnum.artist]: true,
  [DisplaySettingsPropertiesEnum.information]: true,
  [DisplaySettingsPropertiesEnum.tags]: false,
  [DisplaySettingsPropertiesEnum.listens]: false,
};

const SortOptions = {
  releaseDate: {
    value: "release_date",
    label: "Release Date",
  },
  artist: {
    value: "artist_credit_name",
    label: "Artist",
  },
  releaseTitle: {
    value: "release_name",
    label: "Release Title",
  },
  confidence: {
    value: "confidence",
    label: "Confidence",
  },
} as const;

export type SortOption = typeof SortOptions[keyof typeof SortOptions]["value"];

export const filterRangeOptions = {
  week: {
    value: 7,
    key: "week",
    label: "Week",
  },
  month: {
    value: 30,
    key: "month",
    label: "Month",
  },
  three_months: {
    value: 90,
    key: "three_months",
    label: "3 Months",
  },
} as const;

export type filterRangeOption = keyof typeof filterRangeOptions;

export default function FreshReleases() {
  const { APIService, currentUser } = React.useContext(GlobalAppContext);

  const isLoggedIn: boolean = Object.keys(currentUser).length !== 0;
  const PAGE_TYPE_USER: string = "user";
  const PAGE_TYPE_SITEWIDE: string = "sitewide";

  const [releases, setReleases] = React.useState<Array<FreshReleaseItem>>([]);
  const [filteredList, setFilteredList] = React.useState<
    Array<FreshReleaseItem>
  >([]);
  const [allFilters, setAllFilters] = React.useState<{
    releaseTypes: Array<string | undefined>;
    releaseTags: Array<string | undefined>;
  }>({
    releaseTypes: [],
    releaseTags: [],
  });
  const [isLoading, setIsLoading] = React.useState<boolean>(false);
  const [pageType, setPageType] = React.useState<string>(
    isLoggedIn ? PAGE_TYPE_USER : PAGE_TYPE_SITEWIDE
  );

  const [range, setRange] = React.useState<filterRangeOption>("week");
  const [displaySettings, setDisplaySettings] = React.useState<DisplaySettings>(
    initialDisplayState
  );
  const [showPastReleases, setShowPastReleases] = React.useState<boolean>(true);
  const [showFutureReleases, setShowFutureReleases] = React.useState<boolean>(
    true
  );
  const [sort, setSort] = React.useState<SortOption>("release_date");

  const releaseCardGridRef = React.useRef(null);

  const availableSortOptions =
    pageType === PAGE_TYPE_USER
      ? Object.values(SortOptions).filter(
          (option) => option !== SortOptions.confidence
        )
      : Object.values(SortOptions);

  const toggleSettings = (setting: DisplaySettingsPropertiesEnum) => {
    setDisplaySettings({
      ...displaySettings,
      [setting]: !displaySettings[setting],
    });
  };

  React.useEffect(() => {
    const fetchReleases = async () => {
      setIsLoading(true);
      let freshReleases: Array<FreshReleaseItem>;
      try {
        if (pageType === PAGE_TYPE_SITEWIDE) {
          const allFreshReleases = await APIService.fetchSitewideFreshReleases(
            filterRangeOptions[range].value,
            showPastReleases,
            showFutureReleases,
            sort
          );
          freshReleases = allFreshReleases.payload.releases;
        } else {
          const userFreshReleases = await APIService.fetchUserFreshReleases(
            currentUser.name,
            showPastReleases,
            showFutureReleases,
            sort
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

        const uniqueReleaseTagsSet = new Set<string>();
        cleanReleases?.forEach((item) => {
          item.release_tags?.forEach((tag) => {
            uniqueReleaseTagsSet.add(tag);
          });
        });

        const releaseTags = Array.from(uniqueReleaseTagsSet);

        setReleases(cleanReleases);
        setFilteredList(cleanReleases);
        setAllFilters({
          releaseTypes,
          releaseTags,
        });
        setIsLoading(false);
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Couldn't fetch fresh releases"
            message={
              typeof error === "object" ? error.message : error.toString()
            }
          />,
          { toastId: "fetch-error" }
        );
      }
    };
    // Call the async function defined above (useEffect can't return a Promise)
    fetchReleases();
  }, [pageType, range, showPastReleases, showFutureReleases, sort]);

  return (
    <div className="releases-page-container">
      <div className="releases-page">
        <div
          className="fresh-releases-pill-row"
          style={!isLoggedIn ? { justifyContent: "flex-end" } : {}}
        >
          {isLoggedIn ? (
            <div className="fresh-releases-row">
              <Pill
                id="sitewide-releases"
                onClick={() => {
                  setPageType(PAGE_TYPE_SITEWIDE);
                  setSort("release_date");
                }}
                active={pageType === PAGE_TYPE_SITEWIDE}
                type="secondary"
              >
                All
              </Pill>
              <Pill
                id="user-releases"
                onClick={() => setPageType(PAGE_TYPE_USER)}
                active={pageType === PAGE_TYPE_USER}
                type="secondary"
              >
                For You
              </Pill>
            </div>
          ) : null}
          <div className="fresh-releases-row">
            <span>Sort By:</span>{" "}
            <div className="input-group">
              <select
                id="fresh-releases-sort-select"
                className="form-control"
                value={sort}
                onChange={(event) => setSort(event.target.value as SortOption)}
              >
                {availableSortOptions.map((option) => (
                  <option value={option.value} key={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
        <div className="row">
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
            <div id="release-card-grids" ref={releaseCardGridRef}>
              {filteredList.length === 0 ? (
                <div className="no-release">
                  <img
                    src="/static/img/recommendations/no-freshness.png"
                    alt="No Releases Found"
                  />
                </div>
              ) : (
                <ReleaseCardsGrid
                  filteredList={filteredList}
                  displaySettings={displaySettings}
                  order={sort}
                />
              )}

              {pageType === PAGE_TYPE_SITEWIDE && filteredList.length > 0 ? (
                <div className="releases-timeline">
                  <ReleaseTimeline releases={filteredList} order={sort} />
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
      <ReleaseFilters
        allFilters={allFilters}
        releases={releases}
        setFilteredList={setFilteredList}
        range={range}
        handleRangeChange={setRange}
        displaySettings={displaySettings}
        toggleSettings={toggleSettings}
        showPastReleases={showPastReleases}
        setShowPastReleases={setShowPastReleases}
        showFutureReleases={showFutureReleases}
        setShowFutureReleases={setShowFutureReleases}
        releaseCardGridRef={releaseCardGridRef}
        pageType={pageType}
      />
    </div>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, globalAppContext, sentryProps } = getPageProps();
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

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <FreshReleasesPageWithAlertNotifications />
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
