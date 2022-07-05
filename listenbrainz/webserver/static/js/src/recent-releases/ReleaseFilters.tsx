import React from "react";

export default function ReleaseFilters() {
  return (
    <div id="release-filters-container">
      <div id="coverart-checkbox">
        <label className="text-muted">
          <input type="checkbox" id="coverart-only" />
          Releases with cover arts only
        </label>
      </div>
      <div id="release-filters">
        <div id="filters-title-container">
          <div id="filters-title" className="text-muted">
            Type
          </div>
          <div id="clear-btn" className="text-muted">
            clear all
          </div>
        </div>
        <div id="filters-list" />
      </div>
    </div>
  );
}
