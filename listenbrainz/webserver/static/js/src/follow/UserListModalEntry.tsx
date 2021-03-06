import * as React from "react";
import FollowButton from "../FollowButton";
import SimilarityScore from "../SimilarityScore";

export type UserListModalEntryProps = {
  mode: "follow-following" | "similar-users";
  user: ListenBrainzUser;
  loggedInUser: ListenBrainzUser | null;
  loggedInUserFollowsUser: boolean;
  similarityScore: number;
};

const UserListModalEntry = (props: UserListModalEntryProps) => {
  const {
    mode,
    user,
    loggedInUserFollowsUser,
    loggedInUser,
    similarityScore,
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
              similarityScore={similarityScore}
              user={user}
              type="compact"
            />
          )}
        </div>
        {loggedInUser && (
          <FollowButton
            type="block"
            user={{ name: user.name }}
            loggedInUser={loggedInUser}
            loggedInUserFollowsUser={loggedInUserFollowsUser}
          />
        )}
      </div>
    </>
  );
};

UserListModalEntry.defaultProps = {
  mode: "similar-users",
  similarityScore: 0,
};

export default UserListModalEntry;
