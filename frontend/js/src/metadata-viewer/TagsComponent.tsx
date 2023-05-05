import * as React from "react";
import { isFunction } from "lodash";
import TagComponent, { TagActionType } from "./TagComponent";
import GlobalAppContext from "../utils/GlobalAppContext";

function AddTagComponent(props: {
  entityType: "artist" | "release-group" | "recording";
  entityMBID: string;
  callback?: Function;
}) {
  const [expanded, setExpanded] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const { APIService, musicbrainzAuth } = React.useContext(GlobalAppContext);
  const { access_token: musicbrainzAuthToken } = musicbrainzAuth ?? {};
  const { submitTagToMusicBrainz } = APIService;
  const { entityMBID, entityType, callback } = props;

  const submitNewTag = React.useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      const newTag = inputRef?.current?.value;
      if (!newTag || !entityMBID || !musicbrainzAuthToken) {
        return;
      }
      const success = await submitTagToMusicBrainz(
        entityType,
        entityMBID,
        newTag,
        TagActionType.UPVOTE,
        musicbrainzAuthToken
      );
      if (success && isFunction(callback)) {
        callback(newTag);
      }
    },
    [
      entityType,
      entityMBID,
      musicbrainzAuthToken,
      submitTagToMusicBrainz,
      callback,
    ]
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
  const [newTags, setNewTags] = React.useState<EntityTag[]>([]);
  const onAddNewTag = React.useCallback(
    (newTagName: string) => {
      const newTag: EntityTag = { count: 1, tag: newTagName };
      setNewTags((prevTags) => prevTags.concat(newTag));
    },
    [setNewTags]
  );
  const allTags: Array<
    EntityTag | ArtistTag | ReleaseGroupTag
  > = newTags.concat(tags ? tags.filter((tag) => tag.genre_mbid) : []);
  return (
    <div className="tags-wrapper content-box">
      <div className="tags">
        {allTags?.length ? (
          allTags
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
      <AddTagComponent
        entityType={entityType}
        entityMBID={entityMBID}
        callback={onAddNewTag}
      />
    </div>
  );
}
