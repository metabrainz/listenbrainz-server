import * as React from "react";
import { uniqBy } from "lodash";
import Spinner from "react-loader-spinner";
import { toast } from "react-toastify";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { ToastMsg } from "../../notifications/Notifications";
import ReleaseFilters from "./components/ReleaseFilters";
import ReleaseTimeline from "./components/ReleaseTimeline";
import Pill from "../../components/Pill";
import ReleaseCardsGrid from "./components/ReleaseCardsGrid";

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

export const PAGE_TYPE_USER: string = "user";
export const PAGE_TYPE_SITEWIDE: string = "sitewide";

export type filterRangeOption = keyof typeof filterRangeOptions;

export default function FreshReleases() {
  const { APIService, currentUser } = React.useContext(GlobalAppContext);

  const isLoggedIn: boolean = Object.keys(currentUser).length !== 0;

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
        releaseTags.sort();

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
                  alt={
                    releases.length === 0
                      ? "No releases"
                      : "No filtered releases"
                  }
                />
                <div className="text-muted">
                  {releases.length === 0
                    ? "No releases"
                    : `0/${releases.length} releases match your filters.`}
                </div>
              </div>
            ) : (
              <ReleaseCardsGrid
                filteredList={filteredList}
                displaySettings={displaySettings}
                order={sort}
              />
            )}
          </div>
        )}
      </div>
      {pageType === PAGE_TYPE_SITEWIDE && filteredList.length > 0 && (
        <ReleaseTimeline releases={filteredList} order={sort} />
      )}
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
