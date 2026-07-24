import * as React from "react";
import {
  faChevronDown,
  faChevronUp,
  faMagnifyingGlass,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import SideBar from "../../../components/Sidebar";
import Switch from "../../../components/Switch";
import { PlaylistTag, PlaylistType } from "../../../playlists/utils";

type PlaylistActionsSidebarProps = {
  playlistType: PlaylistType;
  sortBy: string;
  sortOptions: React.ReactNode;
  searchTerm: string;
  isLoading?: boolean;
  tags?: PlaylistTag[];
  activeTags: string[];
  onSetPlaylistType: (type: PlaylistType) => void;
  onSortChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onSearchTermChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onSearchKeyEsc: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  onSearchSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  onChangeTags: (tags: string[]) => void;
};

export default function PlaylistActionsSidebar(
  props: PlaylistActionsSidebarProps
) {
  const {
    playlistType,
    sortBy,
    sortOptions,
    searchTerm,
    isLoading = false,
    tags = [],
    activeTags,
    onSetPlaylistType,
    onSortChange,
    onSearchTermChange,
    onSearchKeyEsc,
    onSearchSubmit,
    onChangeTags,
  } = props;

  const [tagsOpen, setTagsOpen] = React.useState(true);
  const [tagFilter, setTagFilter] = React.useState("");

  const selectedTagsSet = React.useMemo(() => new Set(activeTags), [
    activeTags,
  ]);

  const filteredSortedTags = React.useMemo(() => {
    const query = tagFilter.trim().toLowerCase();
    const filtered = query
      ? tags.filter(({ tag }) => tag.toLowerCase().includes(query))
      : tags;

    return [...filtered].sort((a, b) => {
      const aSelected = selectedTagsSet.has(a.tag) ? 0 : 1;
      const bSelected = selectedTagsSet.has(b.tag) ? 0 : 1;
      return aSelected - bSelected;
    });
  }, [tags, tagFilter, selectedTagsSet]);

  const toggleTag = (tag: string) => {
    onChangeTags(
      activeTags.includes(tag)
        ? activeTags.filter((t) => t !== tag)
        : [...activeTags, tag]
    );
  };

  const clearTags = () => {
    onChangeTags([]);
  };

  return (
    <SideBar className="sidebar-playlists">
      <div className="sidebar-header">
        <p>Playlists</p>
        <p>Browse, search, and filter your playlists.</p>
      </div>

      <div className="sidenav-content-grid">
        <div id="playlist-type-label" className="fw-bold">
          Type:
        </div>
        <Switch
          id="playlist-type-playlists"
          value="playlists"
          checked={playlistType === PlaylistType.playlists}
          onChange={() => onSetPlaylistType(PlaylistType.playlists)}
          switchLabel="Playlists"
        />
        <Switch
          id="playlist-type-collaborative"
          value="collaborative"
          checked={playlistType === PlaylistType.collaborations}
          onChange={() => onSetPlaylistType(PlaylistType.collaborations)}
          switchLabel="Collaborative"
        />
      </div>

      <div className="sidenav-content-grid">
        <label className="mb-0" htmlFor="playlist-sidebar-sort">
          Sort by:
        </label>
        <select
          id="playlist-sidebar-sort"
          value={sortBy}
          onChange={onSortChange}
          className="form-select"
          disabled={isLoading}
        >
          {sortOptions}
        </select>
      </div>

      <div className="sidenav-content-grid">
        <label className="mb-0" htmlFor="playlist-sidebar-search">
          Search:
        </label>
        <form
          className="search-bar playlist-sidebar-search"
          onSubmit={onSearchSubmit}
        >
          <input
            id="playlist-sidebar-search"
            type="text"
            className="form-control"
            placeholder="Search playlists"
            value={searchTerm}
            onChange={onSearchTermChange}
            onKeyDown={onSearchKeyEsc}
          />
          <button
            type="submit"
            disabled={isLoading}
            aria-label="Search playlists"
          >
            <FontAwesomeIcon icon={faMagnifyingGlass as IconProp} />
          </button>
        </form>
      </div>

      <div className="sidenav-content-grid">
        <div className="playlist-sidebar-tags-header">
          <div
            className="playlist-sidebar-section-toggle"
            onClick={() => setTagsOpen((open) => !open)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                setTagsOpen((open) => !open);
              }
            }}
            role="button"
            tabIndex={0}
            aria-expanded={tagsOpen}
            aria-controls="playlist-sidebar-tags-panel"
          >
            <h4>
              {tagsOpen ? (
                <FontAwesomeIcon icon={faChevronDown} />
              ) : (
                <FontAwesomeIcon icon={faChevronUp} />
              )}{" "}
              <b>
                Tags
                {activeTags.length > 0 ? ` (${activeTags.length})` : ""}
              </b>
            </h4>
          </div>
          {activeTags.length > 0 && (
            <button
              type="button"
              className="btn btn-link btn-sm playlist-sidebar-clear-tags"
              onClick={clearTags}
            >
              Clear all
            </button>
          )}
        </div>

        <div
          id="playlist-sidebar-tags-panel"
          className="playlist-sidebar-tags-panel"
          hidden={!tagsOpen}
        >
          <input
            id="playlist-sidebar-tag-filter"
            type="search"
            className="form-control playlist-sidebar-tag-filter"
            placeholder="Find tags…"
            value={tagFilter}
            onChange={(e) => setTagFilter(e.target.value)}
            aria-label="Filter tags"
          />
          <div
            className="playlist-sidebar-multiselect"
            role="group"
            aria-label="Filter by tags"
          >
            {filteredSortedTags.map(({ tag, count }) => {
              const checked = selectedTagsSet.has(tag);
              const inputId = `playlist-tag-${tag}`;
              return (
                <label
                  className={`playlist-sidebar-multiselect-option${
                    checked ? " is-selected" : ""
                  }`}
                  key={tag}
                  htmlFor={inputId}
                >
                  <input
                    id={inputId}
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleTag(tag)}
                  />
                  <span className="playlist-sidebar-tag-name">{tag}</span>
                  <span className="playlist-sidebar-tag-count">{count}</span>
                </label>
              );
            })}
            {!filteredSortedTags.length && (
              <div className="text-muted small">
                {tagFilter.trim()
                  ? "No matching tags."
                  : "No tags to show yet."}
              </div>
            )}
          </div>
        </div>
      </div>
    </SideBar>
  );
}
