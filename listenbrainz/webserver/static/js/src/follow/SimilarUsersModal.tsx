import * as React from "react";
import { includes as _includes } from "lodash";

import UserListModalEntry from "./UserListModalEntry";

export type SimilarUsersModalProps = {
  user: ListenBrainzUser;
  loggedInUser: ListenBrainzUser | null;
  similarUsersList: Array<SimilarUser>;
  loggedInUserFollowsUser: (user: ListenBrainzUser | SimilarUser) => boolean;
  updateFollowingList: (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => void;
};

const SimilarUsersModal = (props: SimilarUsersModalProps) => {
  const {
    user,
    loggedInUser,
    loggedInUserFollowsUser,
    updateFollowingList,
    similarUsersList,
  } = props;

  return (
    <>
      <h3 className="text-center">
        Users similar to {user.name === loggedInUser?.name ? "you" : user.name}
      </h3>
      <div className="similar-users-list">
        {similarUsersList.map((listEntry: SimilarUser) => {
          return (
            <UserListModalEntry
              mode="similar-users"
              key={listEntry.name}
              user={listEntry}
              loggedInUser={loggedInUser}
              loggedInUserFollowsUser={loggedInUserFollowsUser(listEntry)}
              updateFollowingList={updateFollowingList}
            />
          );
        })}
      </div>
    </>
  );
};

export default SimilarUsersModal;
