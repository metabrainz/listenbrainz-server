import React, { useState, Dispatch, SetStateAction, useEffect } from "react";

type ReleaseFiltersProps = {
  allFilters: Array<string>;
  releases: Array<FreshReleaseItem>;
  setFilteredList: Dispatch<SetStateAction<Array<FreshReleaseItem>>>;
};

export default function ReleaseFilters(props: ReleaseFiltersProps) {
  const { allFilters, releases, setFilteredList } = props;

  const [checkedList, setCheckedList] = useState<Array<string | undefined>>([]);

  const handleOnChange = (event: React.ChangeEvent<HTMLInputElement>) => {
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

  useEffect(() => {
    const filteredReleases = releases.filter((item) =>
      checkedList.includes(
        item.release_group_primary_type || item.release_group_secondary_type
      )
    );
    setFilteredList(filteredReleases);
  }, [checkedList]);

  return (
    <div id="filters-container">
      <div id="coverart-checkbox">
        <input type="checkbox" id="coverart-only" />
        <label className="text-muted" htmlFor="coverart-only">
          Releases with cover arts only
        </label>
      </div>
      <div id="release-filters">
        <div id="title-container">
          <div id="type-title" className="text-muted">
            Filters
          </div>
          <div id="clearall-btn" className="text-muted" role="button">
            clear all
          </div>
        </div>
        <div id="filters-list">
          {allFilters.map((type, index) => (
            <div>
              <input
                id={`custom-checkbox-${index}`}
                className="type-container"
                type="checkbox"
                value={type}
                checked={checkedList.includes(type)}
                onChange={(e) => handleOnChange(e)}
                aria-hidden="true"
                aria-checked="false"
              />
              <label htmlFor={`custom-checkbox-${index}`}>{type}</label>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
