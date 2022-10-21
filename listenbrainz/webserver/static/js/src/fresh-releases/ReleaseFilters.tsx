import React, { useState, Dispatch, SetStateAction, useEffect } from "react";

type ReleaseFiltersProps = {
  allFilters: Array<string | undefined>;
  releases: Array<FreshReleaseItem>;
  setFilteredList: Dispatch<SetStateAction<Array<FreshReleaseItem>>>;
};

export default function ReleaseFilters(props: ReleaseFiltersProps) {
  const { allFilters, releases, setFilteredList } = props;

  const [checkedList, setCheckedList] = useState<Array<string | undefined>>([]);
  const [coverartOnly, setCoverartOnly] = useState<boolean>(false);

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

  const handleCoverartChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    event.persist();
    const isChecked = event.target.checked;

    if (isChecked) {
      setCoverartOnly(true);
    } else {
      setCoverartOnly(false);
    }
  };

  useEffect(() => {
    // if no filter is chosen, display all releases
    if (checkedList.length === 0) {
      if (coverartOnly === false) {
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
    }
  }, [checkedList, coverartOnly]);

  return (
    <div id="filters-container">
      <div id="coverart-checkbox">
        <label className="text-muted" id="coverart-only">
          <input
            type="checkbox"
            onChange={(e) => handleCoverartChange(e)}
            checked={coverartOnly}
            aria-hidden="true"
            aria-checked="false"
          />
          <span>Hide releases without coverart</span>
        </label>
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
            <span>
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
