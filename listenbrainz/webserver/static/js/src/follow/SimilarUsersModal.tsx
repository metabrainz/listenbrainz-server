import * as React from "react";
import { includes as _includes } from "lodash";

import UserListModalEntry from "./UserListModalEntry";
import GlobalAppContext from "../GlobalAppContext";

export type SimilarUsersModalProps = {
  user: ListenBrainzUser;
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
    loggedInUserFollowsUser,
    updateFollowingList,
    similarUsersList,
  } = props;
  const { currentUser } = React.useContext(GlobalAppContext);

  return (
    <>
      <h3 className="text-center">
        Users similar to {user.name === currentUser?.name ? "you" : user.name}
      </h3>
      <div className="similar-users-list">
        {similarUsersList.map((listEntry: SimilarUser) => {
          return (
            <UserListModalEntry
              mode="similar-users"
              key={listEntry.name}
              user={listEntry}
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
