import { noop, upperFirst } from "lodash";
import * as React from "react";
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
  userScore: UserTagScore;
  withdrawMethod: React.MouseEventHandler;
}) {
  const { action, actionFunction, userScore, withdrawMethod } = props;
  let title = upperFirst(action);
  let isActive = false;
  let onClick = actionFunction;
  // Logic to return the right action depending on the current user score for that tag.
  // We mimic the logic of the MusicBrainz tag vote button component
  // If the score is 0 upvoting and downvoting should do what we expect.
  if (action === TagActionType.UPVOTE) {
    switch (userScore) {
      case -1:
        // If score is -1 and action is "upvote", we withdraw the downvote.
        title = "Withdraw my vote";
        onClick = withdrawMethod;
        break;
      case 1:
        // Already upvoted, do nothing
        isActive = true;
        title = "You’ve upvoted this tag";
        onClick = noop;
        break;
      case 0:
      default:
    }
  }
  if (action === TagActionType.DOWNVOTE) {
    switch (userScore) {
      case -1:
        // Already downvoted
        isActive = true;
        title = "You’ve downvoted this tag";
        onClick = noop;
        break;
      case 1:
        // If score is +1 and action is "downvote", we withdraw the upvote.
        title = "Withdraw my vote";
        onClick = withdrawMethod;
        break;
      case 0:
      default:
    }
  }
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className={`btn tag-vote-button ${action} ${isActive ? "selected" : ""}`}
    >
      {action === TagActionType.UPVOTE ? "+" : "-"}
    </button>
  );
}

export default function TagComponent(props: {
  tag: ArtistTag | RecordingTag | ReleaseGroupTag;
  entityType: "artist" | "release-group" | "recording";
  entityMBID?: string;
}) {
  const { tag, entityType, entityMBID } = props;
  const [userScore, setUserScore] = React.useState<UserTagScore>(0);
  const { APIService } = React.useContext(GlobalAppContext);

  const [upvote, downvote, withdraw] = Object.values(TagActionType).map(
    (actionVerb: TagActionType) => {
      return React.useCallback(async () => {
        let MBID = entityMBID;
        if (entityType === "artist") {
          MBID = (tag as ArtistTag).artist_mbid;
        }
        if (entityType === "release-group") {
          MBID = (tag as ReleaseGroupTag).release_group_mbid;
        }
        if (!MBID) {
          return;
        }
        const success = await APIService.submitTagToMusicBrainz(
          entityType,
          MBID,
          tag.tag,
          actionVerb
        );
        if (success) {
          switch (actionVerb) {
            case TagActionType.UPVOTE:
              setUserScore(1);
              break;
            case TagActionType.DOWNVOTE:
              setUserScore(-1);
              break;
            case TagActionType.WITHDRAW:
            default:
              setUserScore(0);
              break;
          }
        }
      }, [tag, entityType, entityMBID]);
    }
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
      <TagVoteButton
        action={TagActionType.UPVOTE}
        actionFunction={upvote}
        userScore={userScore}
        withdrawMethod={withdraw}
      />
      <TagVoteButton
        action={TagActionType.DOWNVOTE}
        actionFunction={downvote}
        userScore={userScore}
        withdrawMethod={withdraw}
      />
    </span>
  );
}
