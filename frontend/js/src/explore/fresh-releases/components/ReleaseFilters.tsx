import * as React from "react";
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { faCircleXmark } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as _ from "lodash";
import Switch from "../../../components/Switch";
import SideBar from "../../../components/Sidebar";
import type {
  DisplaySettingsPropertiesEnum,
  DisplaySettings,
  filterRangeOption,
} from "../FreshReleases";
import { PAGE_TYPE_SITEWIDE, filterRangeOptions } from "../FreshReleases";

const VARIOUS_ARTISTS_MBID = "89ad4ac3-39f7-470e-963a-56509c546377";

// Special Purpose Artists (SPAs) are placeholders rather than real artists
// (e.g. [unknown], [no artist]) and are not meaningful on the Fresh Releases
// page, so they are hidden by default behind an opt-in toggle. MBIDs are from
// the MusicBrainz style guideline:
// https://musicbrainz.org/doc/Style/Unknown_and_untitled/Special_purpose_artist
// Note: "Various Artists" is also an SPA but is handled by its own filter.
const SPECIAL_PURPOSE_ARTIST_MBIDS = [
  "f731ccc4-e22a-43af-a747-64213329e088", // [anonymous]
  "33cf029c-63b0-41a0-9855-be2a3665fb3b", // [data]
  "314e1c25-dde7-4e4d-b2f4-0a7b9f7c56dc", // [dialogue]
  "eec63d3c-3b81-4ad4-b1e4-7c147d4d2b61", // [no artist]
  "9be7f096-97ec-4615-8957-8d40b5dcbc41", // [traditional]
  "125ec42a-7229-4250-afc5-e057484327fe", // [unknown]
  "7e84f845-ac16-41fe-9ff8-df12eb32af55", // MusicBrainz Test Artist
];

type ReleaseFiltersProps = {
  releases: Array<FreshReleaseItem>;
  releaseTypes: Array<string>;
  releaseTags: Array<string>;
  filteredList: Array<FreshReleaseItem>;
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
    releaseTypes,
    releaseTags,
    releases,
    filteredList,
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

  const [checkedList, setCheckedList] = React.useState<
    Array<string | undefined>
  >([]);
  const [releaseTagsCheckList, setReleaseTagsCheckList] = React.useState<
    Array<string | undefined>
  >([]);
  const [includeVariousArtists, setIncludeVariousArtists] = React.useState<
    boolean
  >(false);
  const [
    includeSpecialPurposeArtists,
    setIncludeSpecialPurposeArtists,
  ] = React.useState<boolean>(false);

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

  // Reset filters when range changes
  React.useEffect(() => {
    setCoverartOnly(false);
    setCheckedList([]);
    setIncludeVariousArtists(false);
    setIncludeSpecialPurposeArtists(false);
  }, [releaseTags, releaseTypes]);

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

      const isVariousArtists = item.artist_mbids.some(
        (mbid) => mbid === VARIOUS_ARTISTS_MBID
      );
      const isVariousArtistsValid = !isVariousArtists || includeVariousArtists;

      const isSpecialPurposeArtist = item.artist_mbids.some((mbid) =>
        SPECIAL_PURPOSE_ARTIST_MBIDS.includes(mbid)
      );
      const isSpecialPurposeArtistValid =
        !isSpecialPurposeArtist || includeSpecialPurposeArtists;

      return (
        isCoverArtValid &&
        isReleaseTypeValid &&
        isReleaseTagValid &&
        !isReleaseTagExcluded &&
        isVariousArtistsValid &&
        isSpecialPurposeArtistValid
      );
    });

    if (!_.isEqual(filteredReleases, filteredList)) {
      setFilteredList(filteredReleases);
    }
    if (releaseCardGridRef.current) {
      window.scrollTo(0, releaseCardGridRef.current.offsetTop);
    }
  }, [
    checkedList,
    releaseTagsCheckList,
    releaseTagsExcludeCheckList,
    coverartOnly,
    includeVariousArtists,
    includeSpecialPurposeArtists,
    releases,
    filteredList,
    releaseCardGridRef,
    setFilteredList,
  ]);

  return (
    <SideBar className="sidebar-fresh-releases">
      <div
        className="sidebar-header"
        data-testid="sidebar-header-fresh-releases"
      >
        <p>Fresh Releases</p>
        <p>Listen to recent releases, and browse what&apos;s dropping soon.</p>
        <p>
          Check out all releases worldwide, or just from artists you&apos;ve
          listened to before, with &apos;for you&apos;.
        </p>
      </div>
      <div className="sidenav-content-grid">
        <div
          onClick={toggleFilters}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              toggleFilters();
            }
          }}
          role="button"
          tabIndex={0}
        >
          <h4>
            {filtersOpen ? (
              <FontAwesomeIcon icon={faChevronDown} />
            ) : (
              <FontAwesomeIcon icon={faChevronUp} />
            )}
            {"  "}
            <b>Filter</b>
          </h4>
        </div>

        {filtersOpen && (
          <>
            <div>
              <label id="range" htmlFor="style">
                Range:{" "}
              </label>
              <select
                id="style"
                className="form-select"
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
            {releaseTypes.length > 0 && (
              <>
                <label id="types" htmlFor="filters-item-1">
                  Types:
                </label>
                {releaseTypes?.map((type, index) => (
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

            {releaseTags.length > 0 && (
              <>
                <label id="tags" htmlFor="include-tags">
                  Include (only):
                </label>
                <select
                  id="include-tags"
                  className="form-select"
                  value=""
                  onChange={handleIncludeTagChange}
                >
                  <option value="" disabled>
                    selection genre/tag...
                  </option>
                  {releaseTags
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

                <label id="tags" htmlFor="exclude-tags">
                  Exclude:
                </label>
                <select
                  id="exclude-tags"
                  className="form-select"
                  value=""
                  onChange={handleExcludeTagChange}
                >
                  <option value="" disabled>
                    selection genre/tag...
                  </option>
                  {releaseTags
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
        <div
          onClick={toggleDisplay}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              toggleDisplay();
            }
          }}
          role="button"
          tabIndex={0}
        >
          <h4>
            {displayOpen ? (
              <FontAwesomeIcon icon={faChevronDown} />
            ) : (
              <FontAwesomeIcon icon={faChevronUp} />
            )}
            {"  "}
            <b>Display</b>
          </h4>
        </div>

        {displayOpen && (
          <>
            <Switch
              id="coverart-only"
              value="coverart-only"
              checked={coverartOnly}
              onChange={(e) => setCoverartOnly(!coverartOnly)}
              switchLabel="Only Releases with artwork"
            />

            <Switch
              id="include-various-artists-switch"
              key="include-various-artists-switch"
              value="various-artists"
              checked={includeVariousArtists}
              onChange={(e) => setIncludeVariousArtists(!includeVariousArtists)}
              switchLabel="Releases by Various Artists"
            />

            <Switch
              id="include-special-purpose-artists-switch"
              key="include-special-purpose-artists-switch"
              value="special-purpose-artists"
              checked={includeSpecialPurposeArtists}
              onChange={(e) =>
                setIncludeSpecialPurposeArtists(!includeSpecialPurposeArtists)
              }
              switchLabel="Releases by special-purpose artists"
            />

            {Object.keys(displaySettings).map((setting, index) =>
              (setting === "Tags" && releaseTags.length === 0) ||
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
    </SideBar>
  );
}
