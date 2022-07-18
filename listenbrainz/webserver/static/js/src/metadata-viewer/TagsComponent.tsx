import * as React from "react";
import TagComponent from "./TagComponent";

function AddTagComponent(props: {
  entityType: "artist" | "release-group" | "recording";
  entityMBID: string;
  callback?: Function;
}) {
  const [expanded, setExpanded] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const { entityMBID, entityType, callback } = props;

  const submitNewTag = React.useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      const newTag = inputRef?.current?.value;
      const requestURL = `https://musicbrainz.org/${entityType}/${entityMBID}/tags/upvote?tags=${newTag}&client=brainzplayer`;
      try {
        const request = await fetch(requestURL, {
          method: "GET",
          mode: "cors",
          credentials: "include",
          headers: {
            Accept: "application/json",
          },
        });
        if (request.ok && callback) {
          callback(newTag);
        }
      } catch (err) {
        console.error(err);
      }
    },
    [entityType, entityMBID]
  );
  return (
    <div className={`add-tag ${expanded ? "expanded" : ""}`}>
      {expanded ? (
        <form className="input-group" onSubmit={submitNewTag}>
          <input
            ref={inputRef}
            type="text"
            minLength={1}
            // eslint-disable-next-line jsx-a11y/no-autofocus
            autoFocus
            placeholder="Enter a new tag…"
            className="form-control"
          />
          <div className="input-group-btn btn-group-sm">
            <button className="btn btn-success" type="submit">
              OK
            </button>
            <button
              title="cancel"
              className="btn btn-danger"
              type="button"
              onClick={() => setExpanded(false)}
            >
              x
            </button>
          </div>
        </form>
      ) : (
        <button
          className="btn btn-xs btn-outline"
          type="button"
          onClick={entityMBID ? () => setExpanded(!expanded) : undefined}
          disabled={!entityMBID}
        >
          + Add tag
        </button>
      )}
    </div>
  );
}

export default function TagsComponent(props: {
  tags?: Array<ArtistTag | RecordingTag | ReleaseGroupTag>;
  entityType: "artist" | "release-group" | "recording";
  entityMBID: string;
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
      <AddTagComponent entityType={entityType} entityMBID={entityMBID} />
    </div>
  );
}
