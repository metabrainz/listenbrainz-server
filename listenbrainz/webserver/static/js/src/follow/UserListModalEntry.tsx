import * as React from "react";
import FollowButton from "../FollowButton";
import SimilarityScore from "../SimilarityScore";
import { SimilarUsersModalProps } from "./SimilarUsersModal";

export type UserListModalEntryProps = {
  mode: "follow-following" | "similar-users";
  user: ListenBrainzUser | SimilarUser;
  loggedInUser: ListenBrainzUser | null;
  apiUrl: string;
  loggedInUserFollowsUser: boolean;
  updateFollowingList: (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => void;
};

const UserListModalEntry = (props: UserListModalEntryProps) => {
  const {
    mode,
    user,
    loggedInUserFollowsUser,
    loggedInUser,
    updateFollowingList,
    apiUrl,
  } = props;
  return (
    <>
      <div key={user.name}>
        <div>
          <a
            href={`/user/${user.name}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            {user.name}
          </a>
          {loggedInUser && mode === "similar-users" && (
            <SimilarityScore
              similarityScore={(user as SimilarUser).similarityScore}
              user={user}
              type="compact"
            />
          )}
        </div>
        {loggedInUser && (
          <FollowButton
            type="block"
            user={user}
            apiUrl={apiUrl}
            loggedInUser={loggedInUser}
            loggedInUserFollowsUser={loggedInUserFollowsUser}
            updateFollowingList={updateFollowingList}
          />
        )}
      </div>
    </>
  );
};

export default UserListModalEntry;
