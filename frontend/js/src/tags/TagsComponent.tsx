import { noop } from "lodash";
import * as React from "react";
import { useCallback, useState } from "react";
import {
  ActionMeta,
  DropdownIndicatorProps,
  MultiValue,
  MultiValueGenericProps,
  components,
} from "react-select";
import CreatableSelect from "react-select/creatable";
import { toast } from "react-toastify";
import TagComponent, { TagActionType } from "./TagComponent";
import GlobalAppContext from "../utils/GlobalAppContext";

type TagOptionType = {
  value: string;
  label: string;
  isFixed?: boolean;
  entityType: Entity;
  entityMBID?: string;
};

function DropdownIndicator(props: DropdownIndicatorProps<TagOptionType>) {
  const { isDisabled } = props;
  if (isDisabled) {
    return null;
  }
  return (
    <components.DropdownIndicator {...props}>
      <button className="btn btn-xs btn-outline" type="button">
        + add genre
      </button>
    </components.DropdownIndicator>
  );
}

function MultiValueContainer(props: MultiValueGenericProps<TagOptionType>) {
  const { data, selectProps } = props;
  return (
    <TagComponent
      tag={{ tag: data.value, count: 1 }}
      entityType={data.entityType}
      entityMBID={data.entityMBID}
      isNew={!data.isFixed}
      deleteCallback={
        data.isFixed
          ? noop
          : (tagName) => {
              selectProps.onChange(selectProps.value, {
                action: "remove-value",
                removedValue: data,
              });
            }
      }
    />
  );
}

export default function AddTagSelect(props: {
  entityType: "artist" | "release-group" | "recording";
  entityMBID?: string;
  tags?: Array<ArtistTag | RecordingTag | ReleaseGroupTag>;
}) {
  const { tags, entityType, entityMBID } = props;
  const [selected, setSelected] = useState<TagOptionType[]>(
    tags?.map((tag) => ({
      value: tag.tag,
      label: tag.tag,
      isFixed: true,
      entityMBID: entityMBID ?? (tag as ArtistTag).artist_mbid ?? undefined,
      entityType,
    })) ?? []
  );

  const { APIService, musicbrainzAuth, musicbrainzGenres } = React.useContext(
    GlobalAppContext
  );
  const { access_token: musicbrainzAuthToken } = musicbrainzAuth ?? {};
  const { submitTagToMusicBrainz } = APIService;

  const submitTagVote = useCallback(
    async (action: TagActionType, tag?: string) => {
      if (!musicbrainzAuthToken) {
        toast.warning(
          "You need to be logged in to MusicBrainz in order to vote on or create tags"
        );
        return false;
      }
      if (!tag || !entityMBID) {
        toast.error(
          "Something went wrong, missing some information to vote on a tag (tag name or entity MBID)"
        );
        return false;
      }
      const success = await submitTagToMusicBrainz(
        entityType,
        entityMBID,
        tag,
        action,
        musicbrainzAuthToken
      );
      if (!success) {
        toast.error("Could not vote on or create tag");
      }
      return success;
    },
    [entityType, entityMBID, musicbrainzAuthToken, submitTagToMusicBrainz]
  );

  const onChange = useCallback(
    async (
      selectedTags: MultiValue<TagOptionType>,
      actionMeta: ActionMeta<TagOptionType>
    ) => {
      let callbackValue: TagOptionType | undefined;

      switch (actionMeta.action) {
        case "select-option":
        case "create-option": {
          callbackValue = actionMeta.option;
          const success = await submitTagVote(
            TagActionType.UPVOTE,
            callbackValue?.value
          );
          if (!success) {
            return;
          }
          setSelected(selectedTags as TagOptionType[]);
          break;
        }
        case "remove-value": {
          callbackValue = actionMeta.removedValue;
          const success = await submitTagVote(
            TagActionType.WITHDRAW,
            callbackValue?.value
          );
          if (!success) {
            return;
          }
          setSelected(
            selectedTags.filter((tag) => tag.value !== callbackValue?.value)
          );
          break;
        }
        default:
          setSelected(selectedTags as TagOptionType[]);
          break;
      }
    },
    [submitTagVote]
  );

  return (
    <div className="add-tag-select">
      <CreatableSelect
        value={selected}
        options={musicbrainzGenres?.map((genre) => ({
          value: genre,
          label: genre,
          entityMBID,
          entityType,
        }))}
        placeholder="Add genre"
        isSearchable
        isMulti
        isDisabled={!musicbrainzAuthToken || !entityMBID}
        isClearable={false}
        openMenuOnClick={false}
        onChange={onChange}
        components={{
          MultiValueContainer,
          DropdownIndicator,
        }}
        styles={{
          container: (baseStyles, state) => ({
            ...baseStyles,
            border: "0px",
          }),
        }}
      />
    </div>
  );
}
