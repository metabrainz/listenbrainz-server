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
  const { APIService, musicbrainzAuth } = React.useContext(GlobalAppContext);
  const { access_token: musicbrainzAuthToken } = musicbrainzAuth ?? {};
  const { submitTagToMusicBrainz } = APIService;

  let tagEntityMBID = entityMBID;
  if (entityType === "artist") {
    tagEntityMBID = (tag as ArtistTag).artist_mbid;
  }
  if (entityType === "release-group") {
    tagEntityMBID = (tag as ReleaseGroupTag).release_group_mbid;
  }
  /** We can't generate the callback frunction from an array.map to refactor this,
   * the callback functions have to be defined separately, duplicating some code.
   */
  const upvote = React.useCallback(async () => {
    if (!tagEntityMBID || !musicbrainzAuthToken) {
      return;
    }
    const success = await submitTagToMusicBrainz(
      entityType,
      tagEntityMBID,
      tag.tag,
      TagActionType.UPVOTE,
      musicbrainzAuthToken
    );
    if (success) {
      setUserScore(1);
    }
  }, [
    tag.tag,
    entityType,
    tagEntityMBID,
    musicbrainzAuthToken,
    submitTagToMusicBrainz,
  ]);

  const downvote = React.useCallback(async () => {
    if (!tagEntityMBID || !musicbrainzAuthToken) {
      return;
    }
    const success = await submitTagToMusicBrainz(
      entityType,
      tagEntityMBID,
      tag.tag,
      TagActionType.DOWNVOTE,
      musicbrainzAuthToken
    );
    if (success) {
      setUserScore(-1);
    }
  }, [
    tag.tag,
    entityType,
    tagEntityMBID,
    musicbrainzAuthToken,
    submitTagToMusicBrainz,
  ]);

  const withdraw = React.useCallback(async () => {
    if (!tagEntityMBID || !musicbrainzAuthToken) {
      return;
    }
    const success = await submitTagToMusicBrainz(
      entityType,
      tagEntityMBID,
      tag.tag,
      TagActionType.WITHDRAW,
      musicbrainzAuthToken
    );
    if (success) {
      setUserScore(0);
    }
  }, [
    tag.tag,
    entityType,
    tagEntityMBID,
    musicbrainzAuthToken,
    submitTagToMusicBrainz,
  ]);

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
