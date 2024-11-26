import * as React from "react";
import { uniqBy } from "lodash";
import Spinner from "react-loader-spinner";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faRss } from "@fortawesome/free-solid-svg-icons";
import NiceModal from "@ebay/nice-modal-react";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { ToastMsg } from "../../notifications/Notifications";
import ReleaseFilters from "./components/ReleaseFilters";
import ReleaseTimeline from "./components/ReleaseTimeline";
import Pill from "../../components/Pill";
import ReleaseCardsGrid from "./components/ReleaseCardsGrid";
import { COLOR_LB_ORANGE } from "../../utils/constants";
import SyndicationFeedModal from "../../components/SyndicationFeedModal";
import { getBaseUrl } from "../../utils/utils";

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

const SortDirections = {
  ascend: {
    value: "ascend",
    label: "Ascending",
  },
  descend: {
    value: "descend",
    label: "Descending",
  },
};

export type SortDirection = typeof SortDirections[keyof typeof SortDirections]["value"];

const DefaultSortDirections: Record<SortOption, SortDirection> = {
  release_date: "descend",
  artist_credit_name: "ascend",
  release_name: "ascend",
  confidence: "descend",
};

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

export const PAGE_TYPE_USER: string = "user";
export const PAGE_TYPE_SITEWIDE: string = "sitewide";

export type filterRangeOption = keyof typeof filterRangeOptions;

type FreshReleasesData = {
  releases: Array<FreshReleaseItem>;
  releaseTypes: Array<string>;
  releaseTags: Array<string>;
};

export default function FreshReleases() {
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const navigate = useNavigate();

  const isLoggedIn: boolean = Object.keys(currentUser).length !== 0;

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
  const [sortDirection, setSortDirection] = React.useState<SortDirection>(
    "descend"
  ); // Default sort direction for release_date
  const [
    hasSelectedSortDirection,
    setHasSelectedSortDirection,
  ] = React.useState(false);

  const releaseCardGridRef = React.useRef(null);

  const availableSortOptions =
    pageType === PAGE_TYPE_SITEWIDE
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

  const queryKey =
    pageType === PAGE_TYPE_SITEWIDE
      ? [
          "fresh-release-sitewide",
          filterRangeOptions[range].value,
          showPastReleases,
          showFutureReleases,
          sort,
        ]
      : [
          "fresh-release-user",
          currentUser.name,
          showPastReleases,
          showFutureReleases,
          sort,
        ];

  const { data: loaderData, isLoading } = useQuery({
    queryKey,
    queryFn: async () => {
      try {
        let freshReleases: Array<FreshReleaseItem>;
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
        releaseTags.sort();

        return {
          data: {
            releases: cleanReleases,
            releaseTypes,
            releaseTags,
          } as FreshReleasesData,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Couldn't fetch fresh releases"
            message={error.message}
          />,
          { toastId: "fetch-error" }
        );
        return {
          data: {
            releases: [],
            releaseTypes: [],
            releaseTags: [],
          } as FreshReleasesData,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const {
    data: rawData = {
      releases: [],
      releaseTypes: [],
      releaseTags: [],
    } as FreshReleasesData,
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const { releases, releaseTypes, releaseTags } = rawData;

  const [filteredList, setFilteredList] = React.useState<
    Array<FreshReleaseItem>
  >(releases);

  let alt;
  let message;
  if (hasError) {
    alt = "Error fetching releases";
    message = `Error fetching releases: ${errorMessage}`;
  } else if (releases.length === 0) {
    alt = "No releases";
    message = "No releases";
  } else {
    alt = "No filtered releases";
    message = `0/${releases.length} releases match your filters.`;
  }

  const handleLoginRedirect = () => {
    toast.warning(
      <ToastMsg
        title="You must be logged in to view personalized releases"
        message="Please log in to view personalized releases"
      />,
      { toastId: "login-error" }
    );

    navigate("/login");
  };

  return (
    <>
      <Helmet>
        <title>Fresh releases</title>
      </Helmet>
      <div className="releases-page-container" role="main">
        <div className="releases-page">
          <div className="fresh-releases-pill-row">
            <div className="fresh-releases-row">
              <Pill
                id="sitewide-releases"
                data-testid="sitewide-releases-pill"
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
                onClick={() => {
                  if (isLoggedIn) {
                    setPageType(PAGE_TYPE_USER);
                  } else {
                    handleLoginRedirect();
                  }
                }}
                active={pageType === PAGE_TYPE_USER}
                type="secondary"
                className={isLoggedIn ? "" : "disabled"}
              >
                For You
              </Pill>
            </div>
            <div className="fresh-releases-row">
              <span>Sort By:</span>{" "}
              <div className="input-group">
                <select
                  id="fresh-releases-sort-select"
                  className="form-control"
                  value={sort}
                  onChange={(event) => {
                    setSort(event.target.value as SortOption);
                    if (!hasSelectedSortDirection) {
                      setSortDirection(
                        DefaultSortDirections[event.target.value as SortOption]
                      );
                    }
                  }}
                >
                  {availableSortOptions.map((option) => (
                    <option value={option.value} key={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <span>Direction:</span>{" "}
              <div className="input-group">
                <select
                  id="fresh-releases-sort-direction-select"
                  className="form-control"
                  value={sortDirection}
                  onChange={(event) => {
                    setSortDirection(event.target.value as SortDirection);
                    setHasSelectedSortDirection(true);
                  }}
                >
                  {Object.entries(SortDirections).map(([_, direction]) => (
                    <option value={direction.value} key={direction.value}>
                      {direction.label}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                className="btn btn-icon btn-info atom-button"
                data-toggle="modal"
                data-target="#SyndicationFeedModal"
                title="Subscribe to syndication feed (Atom)"
                onClick={() => {
                  if (pageType === PAGE_TYPE_SITEWIDE) {
                    NiceModal.show(SyndicationFeedModal, {
                      feedTitle: `Fresh Releases`,
                      options: [
                        {
                          label: "Days",
                          key: "days",
                          type: "number",
                          min: 1,
                          max: 30,
                          defaultValue: 3,
                          tooltip:
                            "Select how many days of past releases to include in the feed, starting from today. Only releases that have already been published will be included.",
                        },
                      ],
                      baseUrl: `${getBaseUrl()}/syndication-feed/fresh-releases`,
                    });
                  } else if (pageType === PAGE_TYPE_USER) {
                    NiceModal.show(SyndicationFeedModal, {
                      feedTitle: `${currentUser.name}'s Fresh Releases`,
                      options: [],
                      baseUrl: `${getBaseUrl()}/syndication-feed/user/${
                        currentUser.name
                      }/fresh-releases`,
                    });
                  }
                }}
              >
                <FontAwesomeIcon icon={faRss} size="sm" />
              </button>
            </div>
          </div>
          {isLoading ? (
            <div className="spinner-container">
              <Spinner
                type="Grid"
                color={COLOR_LB_ORANGE}
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
                    alt={alt}
                  />
                  <div className="text-muted">{message}</div>
                </div>
              ) : (
                <ReleaseCardsGrid
                  filteredList={filteredList}
                  displaySettings={displaySettings}
                  order={sort}
                  direction={sortDirection}
                />
              )}
            </div>
          )}
        </div>
        {filteredList.length > 0 && (
          <ReleaseTimeline
            releases={filteredList}
            order={sort}
            direction={sortDirection}
          />
        )}
        <ReleaseFilters
          releases={releases}
          releaseTypes={releaseTypes}
          releaseTags={releaseTags}
          filteredList={filteredList}
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
    </>
  );
}
