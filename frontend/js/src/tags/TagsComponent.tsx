import { isUndefined, noop } from "lodash";
import * as React from "react";
import { useCallback, useState, useEffect } from "react";
import {
  ActionMeta,
  DropdownIndicatorProps,
  MultiValue,
  MultiValueGenericProps,
  components,
} from "react-select";
import CreatableSelect from "react-select/creatable";
import { toast } from "react-toastify";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import TagComponent, { TagActionType } from "./TagComponent";
import GlobalAppContext from "../utils/GlobalAppContext";

type TagOptionType = {
  value: string;
  label: string;
  isFixed?: boolean;
  isOwnTag?: boolean;
  entityType: Entity;
  entityMBID?: string;
};

function CreateTagText(input: string) {
  return (
    <>
      <FontAwesomeIcon icon={faPlus} /> Submit new tag {input}
    </>
  );
}

function DropdownIndicator(props: DropdownIndicatorProps<TagOptionType>) {
  const { isDisabled } = props;
  if (isDisabled) {
    return null;
  }
  return (
    <components.DropdownIndicator {...props}>
      <button className="btn btn-xs btn-outline" type="button">
        + tag
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
      isOwnTag={data.isOwnTag}
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
function getOptionFromTag(
  tag: ArtistTag | RecordingTag | ReleaseGroupTag,
  entityType: Entity,
  entityMBID?: string
) {
  return {
    value: tag.tag,
    label: tag.tag,
    isFixed: true,
    entityMBID: entityMBID ?? (tag as ArtistTag).artist_mbid ?? undefined,
    entityType,
  };
}

export default function AddTagSelect(props: {
  entityType: "artist" | "release-group" | "recording";
  entityMBID?: string;
  tags?: Array<ArtistTag | RecordingTag | ReleaseGroupTag>;
}) {
  const { tags, entityType, entityMBID } = props;
  const [prevEntityMBID, setPrevEntityMBID] = useState<string>();
  const { APIService, musicbrainzAuth, musicbrainzGenres } = React.useContext(
    GlobalAppContext
  );
  const { access_token: musicbrainzAuthToken } = musicbrainzAuth ?? {};
  const { submitTagToMusicBrainz, MBBaseURI } = APIService;

  const [selected, setSelected] = useState<TagOptionType[]>(
    tags?.length
      ? tags.map((tag) => getOptionFromTag(tag, entityType, entityMBID))
      : []
  );
  const getUserTags = useCallback(async () => {
    /* Get user's own tags */
    if (!musicbrainzAuthToken || !entityType || !entityMBID) {
      return;
    }
    const url = `${MBBaseURI}/${entityType}/${entityMBID}?fmt=json&inc=user-tags`;
    const response = await fetch(encodeURI(url), {
      headers: {
        "Content-Type": "application/xml; charset=utf-8",
        Authorization: `Bearer ${musicbrainzAuthToken}`,
      },
    });
    if (response.ok) {
      const responseJSON = await response.json();
      const userTags = responseJSON["user-tags"];
      if (userTags?.length) {
        setSelected((prevSelected) =>
          userTags
            .map(
              (tag: { name: string }): TagOptionType => ({
                value: tag.name,
                label: tag.name,
                entityType,
                entityMBID,
                isFixed: false,
                isOwnTag: true,
              })
            )
            .concat(prevSelected)
        );
      }
    }
  }, [entityType, entityMBID, musicbrainzAuthToken, MBBaseURI]);

  if (!isUndefined(entityMBID) && prevEntityMBID !== entityMBID) {
    // Will only run once when the entityMBID changes,
    // contrarily to a useEffect with entityMBID as a dependency
    // see https://react.dev/reference/react/useState#my-initializer-or-updater-function-runs-twice
    setPrevEntityMBID(entityMBID);
    try {
      getUserTags();
    } catch (error) {
      toast.error(error.toString());
    }
  }

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
        placeholder="Add tag"
        formatCreateLabel={CreateTagText}
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
