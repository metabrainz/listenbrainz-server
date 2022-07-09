import React from "react";

type ReleaseFiltersProps = {
  filters: Array<string | null>;
};

export default function ReleaseFilters(props: ReleaseFiltersProps) {
  const { filters } = props;
  return (
    <div id="filters-container">
      <div id="coverart-checkbox">
        <label className="text-muted">
          <input type="checkbox" id="coverart-only" />
          Releases with cover arts only
        </label>
      </div>
      <div id="release-filters">
        <div id="title-container">
          <div id="type-title" className="text-muted">
            Type
          </div>
          <div id="clearall-btn" className="text-muted" role="button">
            clear all
          </div>
        </div>
        <div id="filters-list">
          {filters.map((type) => (
            <div className="type-container" role="button">
              <span className="type-name">{type}</span>
              <span className="clear-btn">&times;</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
