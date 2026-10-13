import { isFunction, isUndefined, noop, set, sortBy } from "lodash";
import * as React from "react";
import { useCallback, useMemo, useState, useEffect } from "react";
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
import { ToastMsg } from "../notifications/Notifications";

const originalFetch = window.fetch;
const fetchWithRetry = require("fetch-retry")(originalFetch);

type MBResponseTag = {
  name: string;
  count?: number;
};

type TagOptionType = {
  value: string;
  label: string;
  isNew?: boolean;
  isOwnTag?: boolean;
  entityType: Entity;
  entityMBID?: string;
  originalTag?: ArtistTag | RecordingTag | ReleaseGroupTag;
};

/**
 * Ranks how well a label matches the typed input, without relying on an
 * external fuzzy-matching library. Lower rank = better match.
 * 0 = exact match, 1 = starts with input, 2 = contains input, -1 = no match.
 */
function getMatchRank(label: string, inputValue: string): number {
  const normalizedLabel = label.toLowerCase();
  const normalizedInput = inputValue.toLowerCase();
  if (normalizedLabel === normalizedInput) {
    return 0;
  }
  if (normalizedLabel.startsWith(normalizedInput)) {
    return 1;
  }
  if (normalizedLabel.includes(normalizedInput)) {
    return 2;
  }
  return -1;
}

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
      <button className="btn btn-sm btn-outline-info" type="button">
        + tag
      </button>
    </components.DropdownIndicator>
  );
}

function MultiValueContainer(props: MultiValueGenericProps<TagOptionType>) {
  const { data, selectProps } = props;
  return (
    <TagComponent
      isDisabled={selectProps.isDisabled}
      tag={data.originalTag ?? { tag: data.value, count: 1 }}
      entityType={data.entityType}
      entityMBID={data.entityMBID}
      isNew={data.isNew}
      isOwnTag={data.isOwnTag}
      initialScore={data.isOwnTag ? 1 : 0}
      deleteCallback={
        data.isNew
          ? (tagName) => {
              selectProps.onChange(selectProps.value, {
                action: "remove-value",
                removedValue: data,
              });
            }
          : noop
      }
    />
  );
}
function getOptionFromTag(
  tag: ArtistTag | RecordingTag | ReleaseGroupTag,
  entityType: Entity,
  entityMBID?: string
): TagOptionType {
  return {
    value: tag.tag,
    label: tag.tag,
    isNew: false,
    isOwnTag: false,
    entityMBID: entityMBID ?? (tag as ArtistTag).artist_mbid ?? undefined,
    entityType,
    originalTag: tag,
  };
}

export default function AddTagSelect(props: {
  entityType: "artist" | "release-group" | "recording";
  entityMBID?: string;
  tags?: Array<ArtistTag | RecordingTag | ReleaseGroupTag>;
}) {
  const { tags, entityType, entityMBID } = props;
  const [prevEntityMBID, setPrevEntityMBID] = useState<string>();
  const [inputValue, setInputValue] = useState<string>("");
  const { APIService, musicbrainzAuth, musicbrainzGenres } = React.useContext(
    GlobalAppContext
  );
  const { access_token: musicbrainzAuthToken, refreshMBToken } =
    musicbrainzAuth ?? {};
  const { submitTagToMusicBrainz, MBBaseURI } = APIService;

  const [selected, setSelected] = useState<TagOptionType[]>(
    tags?.map((tag) => getOptionFromTag(tag, entityType, entityMBID)) ?? []
  );

  const getUserTags = useCallback(async () => {
    /* If user is logged in, fetch fresh tags and user's own tags */
    if (!musicbrainzAuthToken || !entityType || !entityMBID) {
      return;
    }
    const url = `${MBBaseURI}/${entityType}/${entityMBID}?fmt=json&inc=user-tags tags`;
    try {
      let token = musicbrainzAuthToken;
      const response = await fetchWithRetry(encodeURI(url), {
        headers: {
          "Content-Type": "application/xml; charset=utf-8",
          Authorization: `Bearer ${token}`,
        },
        async retryOn(attempt: number, error: Error, res: Response) {
          if (attempt >= 3) return false;

          if (error !== null || res.status === 401) {
            if (isFunction(refreshMBToken)) {
              const newToken = await refreshMBToken();
              if (newToken) {
                token = newToken;
                return true;
              }
              return false;
            }
          }
          return false;
        },
      });
      if (response.ok) {
        const responseJSON = await response.json();
        const userTags: MBResponseTag[] = responseJSON["user-tags"];
        if (responseJSON.tags?.length || userTags?.length) {
          const userTagNames: string[] = userTags.map((t) => t.name);
          const formattedTags: TagOptionType[] = responseJSON.tags?.map(
            (tag: MBResponseTag) => ({
              value: tag.name,
              label: tag.name,
              entityType,
              entityMBID,
              isNew: false,
              isOwnTag: false,
              originalTag: { tag: tag.name, count: tag.count },
            })
          );
          // mark the tags that the user has voted on
          formattedTags.forEach((tag) => {
            if (userTagNames.includes(tag.value)) {
              // eslint-disable-next-line no-param-reassign
              tag.isOwnTag = true;
            }
          });
          setSelected(formattedTags);
        }
      }
    } catch (error) {
      toast.error(
        <ToastMsg title="Failed to fetch tags" message={error.toString()} />
      );
    }
  }, [entityType, entityMBID, musicbrainzAuthToken, MBBaseURI, refreshMBToken]);

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
          const newSelection = [...selectedTags];
          const newTag = newSelection.find(
            (tag) => tag.value === callbackValue?.value
          );
          if (newTag) {
            // mark tag as newly created
            newTag.isNew = true;
            newTag.isOwnTag = true;
            // increment the tag count safely
            set(newTag, "originalTag.tag", callbackValue?.value);
            set(
              newTag,
              "originalTag.count",
              (newTag.originalTag?.count ?? 0) + 1
            );
          }
          setSelected(newSelection);
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

  // Build the full option list once from available genres
  const allGenreOptions: TagOptionType[] = useMemo(
    () =>
      musicbrainzGenres?.map((genre) => ({
        value: genre,
        label: genre,
        entityMBID,
        entityType,
      })) ?? [],
    [musicbrainzGenres, entityMBID, entityType]
  );

  // Filter and rank genre options by relevance to what the user has typed,
  // without relying on an external fuzzy-matching library. Options that don't
  // match are dropped; the rest are sorted by match quality (exact, then
  // starts-with, then contains), then alphabetically within each group.
  const filteredSortedOptions: TagOptionType[] = useMemo(() => {
    if (!inputValue) {
      return allGenreOptions;
    }
    return allGenreOptions
      .map((option) => ({
        option,
        rank: getMatchRank(option.label, inputValue),
      }))
      .filter(({ rank }) => rank !== -1)
      .sort((a, b) => {
        if (a.rank !== b.rank) {
          return a.rank - b.rank;
        }
        return a.option.label.localeCompare(b.option.label);
      })
      .map(({ option }) => option);
  }, [allGenreOptions, inputValue]);

  return (
    <div className="add-tag-select">
      <CreatableSelect
        createOptionPosition="first"
        value={sortBy(selected, ["originalTag.count", "isOwnTag"]).reverse()}
        options={filteredSortedOptions}
        // We already filter options ourselves above based on inputValue,
        // so tell react-select not to filter again.
        filterOption={null}
        inputValue={inputValue}
        onInputChange={(newValue) => setInputValue(newValue)}
        placeholder="Add genre or tag"
        formatCreateLabel={CreateTagText}
        isSearchable
        isMulti
        backspaceRemovesValue={false}
        isDisabled={!musicbrainzAuthToken || !entityMBID}
        isClearable={false}
        openMenuOnClick={false}
        onChange={onChange}
        components={{
          MultiValueContainer,
          DropdownIndicator,
        }}
        styles={{
          // @ts-expect-error -> the "!important" in the pointerEvents css rule is not recognized
          container: (baseStyles, state) => ({
            ...baseStyles,
            border: "0px",
            pointerEvents: "initial !important",
          }),
          valueContainer: (styles) => ({
            ...styles,
            flexWrap: "nowrap",
            overflowX: "auto",
            paddingRight: "3.5em",
            scrollbarWidth: "thin",
            "::-webkit-scrollbar": {
              height: "5px",
              backgroundColor: "#f5f5f5",
            },
            "::-webkit-scrollbar-track": {
              backgroundColor: "#f5f5f5",
            },
            ":hover::-webkit-scrollbar-thumb": {
              backgroundColor: "#ccc",
            },
          }),
          indicatorsContainer: (styles) => ({
            ...styles,
            position: "relative",
            ":before": {
              content: "''",
              width: "3em",
              position: "absolute",
              height: "100%",
              left: "-3em",
              background: "linear-gradient(-90deg, white 10%, transparent)",
              pointerEvents: "none",
            },
          }),
        }}
      />
    </div>
  );
}
