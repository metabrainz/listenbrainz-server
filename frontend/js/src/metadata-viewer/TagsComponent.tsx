import * as React from "react";
import TagComponent from "./TagComponent";

function AddTagComponent() {
  const [expanded, setExpanded] = React.useState(false);
  return (
    <div className="add-tag">
      <button
        className="btn btn-xs btn-outline"
        type="button"
        onClick={() => setExpanded(!expanded)}
      >
        + Add tag
      </button>
      {expanded && (
        <form action="">
          <input type="text" />
          <button className="btn btn-xs btn-outline" type="submit">
            OK
          </button>
        </form>
      )}
    </div>
  );
}

export default function TagsComponent(props: {
  tags?: Array<ArtistTag | RecordingTag | ReleaseGroupTag>;
  entityType: "artist" | "release-group" | "recording";
  entityMBID?: string;
}) {
  const { tags, entityType, entityMBID } = props;
  return (
    <div className="tags-wrapper content-box">
      <div className="tags">
        {tags?.length ? (
          tags
            .filter((tag) => tag.genre_mbid)
            .sort((t1, t2) => t2.count - t1.count)
            .map((tag) => (
              <TagComponent
                tag={tag}
                entityType={entityType}
                entityMBID={entityMBID}
              />
            ))
        ) : (
          <span>Be the first to add a tag</span>
        )}
      </div>
      <AddTagComponent />
    </div>
  );
}
