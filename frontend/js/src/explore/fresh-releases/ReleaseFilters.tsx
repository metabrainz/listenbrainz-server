import * as React from "react";
import {
  faChevronDown,
  faChevronUp,
  faGear,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { faCircleXmark } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import Switch from "../../components/Switch";
import type {
  DisplaySettingsPropertiesEnum,
  DisplaySettings,
  filterRangeOption,
} from "./FreshReleases";
import { PAGE_TYPE_SITEWIDE, filterRangeOptions } from "./FreshReleases";

type ReleaseFiltersProps = {
  allFilters: {
    releaseTypes: Array<string | undefined>;
    releaseTags: Array<string | undefined>;
  };
  releases: Array<FreshReleaseItem>;
  setFilteredList: React.Dispatch<
    React.SetStateAction<Array<FreshReleaseItem>>
  >;
  range: string;
  handleRangeChange: (range: filterRangeOption) => void;
  displaySettings: DisplaySettings;
  toggleSettings: (setting: DisplaySettingsPropertiesEnum) => void;
  showPastReleases: boolean;
  setShowPastReleases: React.Dispatch<React.SetStateAction<boolean>>;
  showFutureReleases: boolean;
  setShowFutureReleases: React.Dispatch<React.SetStateAction<boolean>>;
  releaseCardGridRef: React.RefObject<HTMLDivElement>;
  pageType: string;
};

export default function ReleaseFilters(props: ReleaseFiltersProps) {
  const {
    allFilters,
    releases,
    setFilteredList,
    range,
    handleRangeChange,
    displaySettings,
    toggleSettings,
    showPastReleases,
    setShowPastReleases,
    showFutureReleases,
    setShowFutureReleases,
    releaseCardGridRef,
    pageType,
  } = props;

  // TODO: Refactor this functionality in a reusable Sidebar component
  const [isSidebarOpen, setIsSidebarOpen] = React.useState<boolean>(false);
  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const [checkedList, setCheckedList] = React.useState<
    Array<string | undefined>
  >([]);
  const [releaseTagsCheckList, setReleaseTagsCheckList] = React.useState<
    Array<string | undefined>
  >([]);

  const [
    releaseTagsExcludeCheckList,
    setReleaseTagsExcludeCheckList,
  ] = React.useState<Array<string | undefined>>([]);
  const [coverartOnly, setCoverartOnly] = React.useState<boolean>(false);
  const [filtersOpen, setFiltersOpen] = React.useState<boolean>(true);
  const [displayOpen, setDisplayOpen] = React.useState<boolean>(true);

  const toggleFilters = () => {
    setFiltersOpen(!filtersOpen);
  };

  const toggleDisplay = () => {
    setDisplayOpen(!displayOpen);
  };

  const handleFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    event.persist();
    const { value } = event.target;
    const isChecked = event.target.checked;

    if (isChecked) {
      setCheckedList([...checkedList, value]);
    } else {
      const filtersList = checkedList.filter((item) => item !== value);
      setCheckedList(filtersList);
    }
  };

  const handleIncludeTagChange = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    event.preventDefault();
    const { value } = event.target;
    setReleaseTagsCheckList([...releaseTagsCheckList, value]);

    // remove from exclude list if it's there
    const filtersList = releaseTagsExcludeCheckList.filter(
      (item) => item !== value
    );
    setReleaseTagsExcludeCheckList(filtersList);
  };

  const removeFilterTag = (tag: string) => {
    const filtersList = releaseTagsCheckList.filter((item) => item !== tag);
    setReleaseTagsCheckList(filtersList);
  };

  const handleExcludeTagChange = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    event.preventDefault();
    const { value } = event.target;
    setReleaseTagsExcludeCheckList([...releaseTagsExcludeCheckList, value]);

    // remove from include list if it's there
    const filtersList = releaseTagsCheckList.filter((item) => item !== value);
    setReleaseTagsCheckList(filtersList);
  };

  const removeExcludeTag = (tag: string) => {
    const filtersList = releaseTagsExcludeCheckList.filter(
      (item) => item !== tag
    );
    setReleaseTagsExcludeCheckList(filtersList);
  };

  const handleRangeDropdown = (event: React.ChangeEvent<HTMLSelectElement>) => {
    event.persist();
    const value = event.target.value as filterRangeOption;
    handleRangeChange(value);
  };

  const totalListenCount = releases.reduce(
    (accumulator, currentRelease) => accumulator + currentRelease.listen_count,
    0
  );

  const availableRangeOptions =
    pageType === PAGE_TYPE_SITEWIDE
      ? Object.values(filterRangeOptions).filter(
          (option) => option !== filterRangeOptions.three_months
        )
      : Object.values(filterRangeOptions);

  React.useEffect(() => {
    setCoverartOnly(false);
    setCheckedList([]);
  }, [allFilters]);

  React.useEffect(() => {
    const filteredReleases = releases.filter((item) => {
      const isCoverArtValid =
        !coverartOnly || (coverartOnly && item.caa_id !== null);
      const isReleaseTypeValid =
        checkedList.length === 0 ||
        checkedList.includes(
          item.release_group_secondary_type || item.release_group_primary_type
        );
      const isReleaseTagValid =
        releaseTagsCheckList.length === 0 ||
        item.release_tags?.some((tag) => releaseTagsCheckList.includes(tag));
      const isReleaseTagExcluded = item.release_tags?.some((tag) =>
        releaseTagsExcludeCheckList.includes(tag)
      );

      return (
        isCoverArtValid &&
        isReleaseTypeValid &&
        isReleaseTagValid &&
        !isReleaseTagExcluded
      );
    });

    setFilteredList(filteredReleases);
    if (releaseCardGridRef.current) {
      window.scrollTo(0, releaseCardGridRef.current.offsetTop);
    }
  }, [
    checkedList,
    releaseTagsCheckList,
    releaseTagsExcludeCheckList,
    coverartOnly,
  ]);

  return (
    <>
      <div className={`sidebar ${isSidebarOpen ? "open" : ""}`}>
        <div id="sidebar-fresh-release">
          <p>Fresh Releases</p>
          <p>
            Listen to recent releases, and browse what&apos;s dropping soon.
          </p>
          <p>
            Check out all releases worldwide, or just from artists you&apos;ve
            listened to before, with &apos;for you&apos;.
          </p>
        </div>
        <div className="sidenav-content-grid">
          <h4>
            {filtersOpen ? (
              <FontAwesomeIcon icon={faChevronDown} onClick={toggleFilters} />
            ) : (
              <FontAwesomeIcon icon={faChevronUp} onClick={toggleFilters} />
            )}
            {"  "}
            <b>Filter</b>
          </h4>

          {filtersOpen && (
            <>
              <div id="range">Range: </div>

              <div className="input-group">
                <select
                  id="style"
                  className="form-control"
                  value={range}
                  onChange={handleRangeDropdown}
                >
                  {availableRangeOptions.map((option) => (
                    <option value={option.key} key={option.key}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <Switch
                id="date-filter-item-past"
                value="past"
                checked={showPastReleases}
                onChange={(e) => setShowPastReleases(!showPastReleases)}
                switchLabel="Past"
              />
              <Switch
                id="date-filter-item-future"
                value="future"
                checked={showFutureReleases}
                onChange={(e) => setShowFutureReleases(!showFutureReleases)}
                switchLabel="Future"
              />
              {allFilters.releaseTypes.length > 0 && (
                <>
                  <span id="types">Types:</span>
                  {allFilters.releaseTypes?.map((type, index) => (
                    <Switch
                      id={`filters-item-${index}`}
                      key={`filters-item-${type}`}
                      value={type}
                      checked={checkedList?.includes(type)}
                      onChange={handleFilterChange}
                      switchLabel={type}
                    />
                  ))}
                </>
              )}

              {allFilters.releaseTags.length > 0 && (
                <>
                  <span id="tags">Include (only):</span>
                  <select
                    id="include-tags"
                    className="form-control"
                    value=""
                    onChange={handleIncludeTagChange}
                  >
                    <option value="" disabled>
                      selection genre/tag...
                    </option>
                    {allFilters.releaseTags
                      ?.filter((tag) => !releaseTagsCheckList.includes(tag))
                      ?.map((tag, index) => (
                        <option value={tag} key={tag}>
                          {tag}
                        </option>
                      ))}
                  </select>

                  <div className="release-tags">
                    {releaseTagsCheckList?.map((tag, index) => (
                      <div id={`include-tag-item-${index}`} className="tags">
                        <span className="release-tag-name">{tag}</span>
                        <FontAwesomeIcon
                          icon={faCircleXmark}
                          onClick={() => removeFilterTag(tag!)}
                        />
                      </div>
                    ))}
                  </div>

                  <span id="tags">Exclude:</span>
                  <select
                    id="style"
                    className="form-control"
                    value=""
                    onChange={handleExcludeTagChange}
                  >
                    <option value="" disabled>
                      selection genre/tag...
                    </option>
                    {allFilters.releaseTags
                      ?.filter(
                        (tag) => !releaseTagsExcludeCheckList.includes(tag)
                      )
                      ?.map((tag, index) => (
                        <option value={tag} key={tag}>
                          {tag}
                        </option>
                      ))}
                  </select>

                  <div className="release-tags">
                    {releaseTagsExcludeCheckList?.map((tag, index) => (
                      <div id={`exclude-tag-item-${index}`} className="tags">
                        <span className="release-tag-name">{tag}</span>
                        <FontAwesomeIcon
                          icon={faCircleXmark}
                          onClick={() => removeExcludeTag(tag!)}
                        />
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          )}
        </div>
        <div className="sidenav-content-grid">
          <h4>
            {displayOpen ? (
              <FontAwesomeIcon icon={faChevronDown} onClick={toggleDisplay} />
            ) : (
              <FontAwesomeIcon icon={faChevronUp} onClick={toggleDisplay} />
            )}
            {"  "}
            <b>Display</b>
          </h4>

          {displayOpen && (
            <>
              <Switch
                id="coverart-only"
                value="coverart-only"
                checked={coverartOnly}
                onChange={(e) => setCoverartOnly(!coverartOnly)}
                switchLabel="Only Releases with artwork"
              />

              {Object.keys(displaySettings).map((setting, index) =>
                (setting === "Tags" && allFilters.releaseTags.length === 0) ||
                (setting === "Listens" && !totalListenCount) ? null : (
                  <Switch
                    id={`display-item-${index}`}
                    key={`display-item-${setting}`}
                    value={setting}
                    checked={
                      displaySettings[setting as DisplaySettingsPropertiesEnum]
                    }
                    onChange={(e) =>
                      toggleSettings(setting as DisplaySettingsPropertiesEnum)
                    }
                    switchLabel={setting}
                  />
                )
              )}
            </>
          )}
        </div>
      </div>
      <button
        className={`toggle-sidebar-button ${isSidebarOpen ? "open" : ""}`}
        onClick={toggleSidebar}
        type="button"
      >
        <FontAwesomeIcon icon={isSidebarOpen ? faXmark : faGear} size="2x" />
      </button>
      {isSidebarOpen && (
        <button
          className="sidebar-overlay"
          onClick={toggleSidebar}
          type="button"
        >
          {}
        </button>
      )}
    </>
  );
}
