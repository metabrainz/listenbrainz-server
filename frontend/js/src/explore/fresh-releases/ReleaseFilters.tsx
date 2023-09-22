import * as React from "react";
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import Switch from "../../components/Switch";

type ReleaseFiltersProps = {
  allFilters: Array<string | undefined>;
  releases: Array<FreshReleaseItem>;
  setFilteredList: React.Dispatch<
    React.SetStateAction<Array<FreshReleaseItem>>
  >;
  range: string;
  handleRangeChange: (childData: string) => void;
  displaySettings: { [key: string]: boolean };
  toggleSettings: (setting: string) => void;
  showPastReleases: boolean;
  setShowPastReleases: React.Dispatch<React.SetStateAction<boolean>>;
  showFutureReleases: boolean;
  setShowFutureReleases: React.Dispatch<React.SetStateAction<boolean>>;
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
  } = props;

  const [checkedList, setCheckedList] = React.useState<
    Array<string | undefined>
  >([]);
  const [coverartOnly, setCoverartOnly] = React.useState<boolean>(false);
  const [filtersOpen, setFiltersOpen] = React.useState<boolean>(true);

  const toggleFilters = () => {
    setFiltersOpen(!filtersOpen);
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

  const handleRangeDropdown = (event: React.ChangeEvent<HTMLSelectElement>) => {
    event.persist();
    const { value } = event.target;
    handleRangeChange(value);
  };

  React.useEffect(() => {
    // if no filter is chosen, display all releases
    if (checkedList.length === 0) {
      if (!coverartOnly) {
        setFilteredList(releases);
      } else {
        setFilteredList(releases.filter((item) => item.caa_id !== null));
      }
    } else {
      const filteredReleases = releases.filter((item) => {
        if (coverartOnly) {
          return (
            item.caa_id !== null &&
            checkedList.includes(
              item.release_group_secondary_type ||
                item.release_group_primary_type
            )
          );
        }
        return checkedList.includes(
          item.release_group_secondary_type || item.release_group_primary_type
        );
      });
      setFilteredList(filteredReleases);

      window.scrollTo(
        0,
        document.getElementById("release-cards-grid")!.offsetTop
      );
    }
  }, [checkedList, coverartOnly]);

  return (
    <div className="sidebar settings-navbar">
      <div className="basic-settings-container">
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
          <div id="range">Range: </div>

          <div className="input-group">
            <select
              id="style"
              className="form-control"
              value={range}
              onChange={handleRangeDropdown}
            >
              <option value="week">1 Week</option>
              <option value="month">1 Month</option>
              <option value="three_months">3 Month</option>
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
          {allFilters.length > 0 && (
            <>
              <span id="types">Types:</span>
              {allFilters.map((type, index) => (
                <Switch
                  id={`filters-item-${index}`}
                  value={type}
                  checked={checkedList.includes(type)}
                  onChange={handleFilterChange}
                  switchLabel={type}
                />
              ))}
            </>
          )}
        </div>
      </div>
      <div className="basic-settings-container">
        <div className="sidenav-content-grid">
          <h4>
            {filtersOpen ? (
              <FontAwesomeIcon icon={faChevronDown} onClick={toggleFilters} />
            ) : (
              <FontAwesomeIcon icon={faChevronUp} onClick={toggleFilters} />
            )}
            {"  "}
            <b>Display</b>
          </h4>

          <Switch
            id="coverart-only"
            value="coverart-only"
            checked={coverartOnly}
            onChange={(e) => setCoverartOnly(!coverartOnly)}
            switchLabel="Only Releases with artwork"
          />

          {Object.keys(displaySettings).map((setting, index) => (
            <Switch
              id={`display-item-${index}`}
              value={setting}
              checked={displaySettings[setting]}
              onChange={(e) => toggleSettings(setting)}
              switchLabel={setting}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
