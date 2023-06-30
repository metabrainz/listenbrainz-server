import { noop, upperFirst } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTimes, faPlus, faMinus } from "@fortawesome/free-solid-svg-icons";

import * as React from "react";
import { toast } from "react-toastify";
import GlobalAppContext from "../utils/GlobalAppContext";

type UserTagScore = 0 | 1 | -1;

export enum TagActionType {
  UPVOTE = "upvote",
  DOWNVOTE = "downvote",
  WITHDRAW = "withdraw",
}

function TagVoteButton(props: {
  action: TagActionType;
  actionFunction: React.MouseEventHandler;
  userScore?: UserTagScore;
  withdrawMethod?: React.MouseEventHandler;
}) {
  const { action, actionFunction, userScore, withdrawMethod } = props;
  let title = upperFirst(action);
  let isActive = false;
  let onClick = actionFunction;
  let buttonContent;

  if (action === TagActionType.WITHDRAW) {
    buttonContent = <FontAwesomeIcon icon={faTimes} fixedWidth />;
  }
  if (action === TagActionType.UPVOTE) {
    buttonContent = <FontAwesomeIcon icon={faPlus} fixedWidth />;
    switch (userScore) {
      case 1:
        // Already upvoted, do nothing
        isActive = true;
        title = "Withdraw my vote";
        onClick = withdrawMethod ?? noop;
        break;
      default:
        title = "Upvote";
        onClick = actionFunction;
        break;
    }
  }
  if (action === TagActionType.DOWNVOTE) {
    buttonContent = <FontAwesomeIcon icon={faMinus} fixedWidth />;
    switch (userScore) {
      case -1:
        // Already downvoted
        isActive = true;
        title = "Withdraw my vote";
        onClick = withdrawMethod ?? noop;
        break;
      default:
        title = "Downvote";
        onClick = actionFunction;
        break;
    }
  }
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className={`btn tag-vote-button ${action} ${isActive ? "selected" : ""}`}
    >
      {buttonContent}
    </button>
  );
}

export default function TagComponent(props: {
  tag: ArtistTag | RecordingTag | ReleaseGroupTag;
  entityType: "artist" | "release-group" | "recording";
  entityMBID?: string;
  isNew?: boolean;
  deleteCallback: (tag: string) => void;
}) {
  const { tag, entityType, entityMBID, isNew, deleteCallback } = props;
  // TODO: Fetch user's tag votes for this entity? That's a lot of API queries…
  const [userScore, setUserScore] = React.useState<UserTagScore>(0);
  const { APIService, musicbrainzAuth } = React.useContext(GlobalAppContext);
  const { access_token: musicbrainzAuthToken } = musicbrainzAuth ?? {};
  const { submitTagToMusicBrainz } = APIService;

  let tagEntityMBID = entityMBID;
  if (entityType === "artist") {
    tagEntityMBID = (tag as ArtistTag).artist_mbid;
  }

  /** We can't generate the callback frunction from an array.map to refactor this,
   * the callback functions have to be defined separately, duplicating some code.
   */
  const vote = React.useCallback(
    async (action: TagActionType) => {
      if (!tagEntityMBID || !musicbrainzAuthToken) {
        return;
      }
      const success = await submitTagToMusicBrainz(
        entityType,
        tagEntityMBID,
        tag.tag,
        action,
        musicbrainzAuthToken
      );
      if (success) {
        switch (action) {
          case TagActionType.UPVOTE:
            setUserScore(1);
            break;
          case TagActionType.DOWNVOTE:
            setUserScore(-1);
            break;
          default:
            setUserScore(0);
            break;
        }
      } else {
        toast.error("Could not vote on or create tag");
      }
    },
    [
      tag.tag,
      entityType,
      tagEntityMBID,
      musicbrainzAuthToken,
      submitTagToMusicBrainz,
    ]
  );

  return (
    <span key={tag.tag + tag.count} className="tag">
      <a
        href={`https://musicbrainz.org/tag/${tag.tag}`}
        target="_blank"
        title={`${tag.tag} on MusicBrainz`}
        rel="noopener noreferrer"
      >
        {tag.tag}
      </a>
      {isNew ? (
        <TagVoteButton
          action={TagActionType.WITHDRAW}
          actionFunction={(e) => {
            deleteCallback(tag.tag);
          }}
          userScore={1}
        />
      ) : (
        <>
          <TagVoteButton
            action={TagActionType.UPVOTE}
            actionFunction={() => {
              vote(TagActionType.UPVOTE);
            }}
            userScore={userScore}
            withdrawMethod={() => {
              vote(TagActionType.WITHDRAW);
            }}
          />
          <TagVoteButton
            action={TagActionType.DOWNVOTE}
            actionFunction={() => {
              vote(TagActionType.DOWNVOTE);
            }}
            userScore={userScore}
            withdrawMethod={() => {
              vote(TagActionType.WITHDRAW);
            }}
          />
        </>
      )}
    </span>
  );
}
