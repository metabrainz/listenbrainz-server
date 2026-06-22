import * as React from "react";

export type PlaylistTag = {
  tag: string;
  count: number;
};

export default function PlaylistTagsSidebar(props: {
  tags: PlaylistTag[];
  activeTags: string[];
  onChangeTags: (tags: string[]) => void;
}) {
  const { tags, activeTags, onChangeTags } = props;
  const activeTagsSet = React.useMemo(() => new Set(activeTags), [activeTags]);

  return (
    <div className="playlist-tags-sidebar">
      <div className="playlist-tags-header">
        <span className="playlist-tags-title">Filter by Tags</span>
        {activeTags.length > 0 && (
          <button
            type="button"
            className="btn btn-link btn-sm playlist-tags-clear"
            onClick={() => onChangeTags([])}
          >
            Clear all
          </button>
        )}
      </div>
      {activeTags.length > 0 && (
        <div className="playlist-tags-selected">
          {activeTags.map((tag) => (
            <button
              key={tag}
              type="button"
              className="playlist-tag-chip"
              onClick={() => {
                onChangeTags(activeTags.filter((t) => t !== tag));
              }}
              title="Remove tag"
            >
              {tag} <span className="playlist-tag-chip-x">×</span>
            </button>
          ))}
        </div>
      )}
      <div className="playlist-tags-list">
        {tags.map(({ tag, count }) => {
          const isActive = activeTagsSet.has(tag);
          return (
            <button
              key={tag}
              type="button"
              className={`playlist-tag-row ${isActive ? "active" : ""}`}
              onClick={() => {
                if (isActive) {
                  onChangeTags(activeTags.filter((t) => t !== tag));
                } else {
                  onChangeTags([...activeTags, tag]);
                }
              }}
            >
              <span className="playlist-tag-dot" />
              <span className="playlist-tag-name">{tag}</span>
              <span className="playlist-tag-count">{count}</span>
            </button>
          );
        })}
        {!tags.length && (
          <div className="text-muted small">No tags to show yet.</div>
        )}
      </div>
    </div>
  );
}
