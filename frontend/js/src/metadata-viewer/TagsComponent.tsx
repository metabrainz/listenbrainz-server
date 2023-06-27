import * as React from "react";
import { isFunction } from "lodash";
import Select, { ActionMeta, SingleValue } from "react-select";
import TagComponent, { TagActionType } from "./TagComponent";
import GlobalAppContext from "../utils/GlobalAppContext";

type TagOptionType = {
  value: string;
  label: string;
};

function AddTagComponent(props: {
  entityType: "artist" | "release-group" | "recording";
  entityMBID: string;
  callback?: Function;
}) {
  const [expanded, setExpanded] = React.useState(false);
  const { APIService, musicbrainzAuth, musicbrainzGenres } = React.useContext(
    GlobalAppContext
  );
  const { access_token: musicbrainzAuthToken } = musicbrainzAuth ?? {};
  const { submitTagToMusicBrainz } = APIService;
  const { entityMBID, entityType, callback } = props;

  const submitNewTag = React.useCallback(
    async (
      selectedTag: SingleValue<TagOptionType>,
      actionMeta: ActionMeta<TagOptionType>
    ) => {
      if (!selectedTag?.value || !entityMBID || !musicbrainzAuthToken) {
        return;
      }
      if (!["select-option", "create-option"].includes(actionMeta.action)) {
        return;
      }
      const success = await submitTagToMusicBrainz(
        entityType,
        entityMBID,
        selectedTag.value,
        TagActionType.UPVOTE,
        musicbrainzAuthToken
      );
      if (success && isFunction(callback)) {
        callback(selectedTag);
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
        <Select
          options={musicbrainzGenres?.map((genre) => ({
            value: genre,
            label: genre,
          }))}
          isSearchable
          onChange={submitNewTag}
          onMenuClose={() => setExpanded(false)}
        />
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
