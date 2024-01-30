import * as React from "react";
import { includes as _includes } from "lodash";

import UserListModalEntry from "./UserListModalEntry";
import GlobalAppContext from "../../../utils/GlobalAppContext";

export type SimilarUsersModalProps = {
  user: ListenBrainzUser;
  similarUsersList: Array<SimilarUser>;
  loggedInUserFollowsUser: (user: ListenBrainzUser | SimilarUser) => boolean;
  updateFollowingList: (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => void;
};

function SimilarUsersModal(props: SimilarUsersModalProps) {
  const {
    user,
    loggedInUserFollowsUser,
    updateFollowingList,
    similarUsersList,
  } = props;
  const { currentUser } = React.useContext(GlobalAppContext);

  const renderSimilarUsersList = React.useCallback(() => {
    if (similarUsersList.length === 0) {
      return (
        <>
          <hr />
          <div className="similar-users-empty text-center text-muted">
            Users with similar music tastes to{" "}
            {user.name === currentUser?.name ? "you" : user.name} will appear
            here.
          </div>
        </>
      );
    }
    return (
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
    );
  }, [
    similarUsersList,
    user,
    currentUser,
    loggedInUserFollowsUser,
    updateFollowingList,
  ]);

  return (
    <>
      <h3 className="text-center" style={{ marginTop: "10px" }}>
        Similar Users
      </h3>
      {renderSimilarUsersList()}
    </>
  );
}

export default SimilarUsersModal;
