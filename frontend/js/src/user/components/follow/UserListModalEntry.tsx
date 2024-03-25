import { isEmpty, isNil } from "lodash";
import * as React from "react";
import { useContext } from "react";
import { Link } from "react-router-dom";
import FollowButton from "./FollowButton";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import SimilarityScore from "./SimilarityScore";

export type UserListModalEntryProps = {
  mode: "follow-following" | "similar-users";
  user: ListenBrainzUser | SimilarUser;
  loggedInUserFollowsUser: boolean;
  updateFollowingList: (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => void;
};

function UserListModalEntry(props: UserListModalEntryProps) {
  const { mode, user, loggedInUserFollowsUser, updateFollowingList } = props;
  const { currentUser } = useContext(GlobalAppContext);
  const isUserLoggedIn = !isNil(currentUser) && !isEmpty(currentUser);
  return (
    <div key={user.name}>
      <div>
        <Link to={`/user/${user.name}/`}>{user.name}</Link>
        {isUserLoggedIn && mode === "similar-users" && (
          <SimilarityScore
            similarityScore={(user as SimilarUser).similarityScore}
            user={user}
            type="compact"
          />
        )}
      </div>
      {isUserLoggedIn && (
        <FollowButton
          type="block"
          user={user}
          loggedInUserFollowsUser={loggedInUserFollowsUser}
          updateFollowingList={updateFollowingList}
        />
      )}
    </div>
  );
}

export default UserListModalEntry;
