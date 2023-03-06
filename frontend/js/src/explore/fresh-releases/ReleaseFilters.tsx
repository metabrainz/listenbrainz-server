import * as React from "react";
import Pill from "../../components/Pill";

type ReleaseFiltersProps = {
  allFilters: Array<string | undefined>;
  releases: Array<FreshReleaseItem>;
  setFilteredList: React.Dispatch<
    React.SetStateAction<Array<FreshReleaseItem>>
  >;
};

export default function ReleaseFilters(props: ReleaseFiltersProps) {
  const { allFilters, releases, setFilteredList } = props;

  const [checkedList, setCheckedList] = React.useState<
    Array<string | undefined>
  >([]);
  const [coverartOnly, setCoverartOnly] = React.useState<boolean>(false);

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
    <div id="filters-container">
      <div id="coverart-checkbox">
        <Pill
          type="secondary"
          active={coverartOnly}
          onClick={() => setCoverartOnly(!coverartOnly)}
          style={{
            padding: "4px 12px",
            margin: "unset",
          }}
        >
          Hide releases without coverart
        </Pill>
      </div>
      <div id="release-filters">
        <div id="title-container">
          <div id="type-title" className="text-muted">
            Filters
          </div>
          <div
            id={
              checkedList.length === 0
                ? "clearall-btn-inactive"
                : "clearall-btn-active"
            }
            className="text-muted"
            role="button"
            onClick={() => setCheckedList([])}
            aria-hidden="true"
          >
            &times;
          </div>
        </div>
        <div id="filters-list">
          {allFilters.map((type, index) => (
            <span key={`filter-${type}`}>
              <input
                id={`filters-item-${index}`}
                className="type-container"
                type="checkbox"
                value={type}
                checked={checkedList.includes(type)}
                onChange={(e) => handleFilterChange(e)}
                aria-hidden="true"
                aria-checked="false"
              />
              <label
                htmlFor={`filters-item-${index}`}
                className={
                  checkedList.includes(type)
                    ? "type-name-active"
                    : "type-name-inactive"
                }
              >
                {type}
              </label>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
