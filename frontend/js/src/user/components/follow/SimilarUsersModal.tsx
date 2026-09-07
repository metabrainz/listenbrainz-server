import * as React from "react";
import { includes as _includes } from "lodash";

import UserListModalEntry from "./UserListModalEntry";
import GlobalAppContext from "../../../utils/GlobalAppContext";

export type SimilarUsersModalProps = {
  userName: string;
  similarUsersList: Array<SimilarUser>;
  loggedInUserFollowsUser: (user: ListenBrainzUser | SimilarUser) => boolean;
  updateFollowingList: (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => void;
};

function SimilarUsersModal(props: SimilarUsersModalProps) {
  const {
    userName,
    loggedInUserFollowsUser,
    updateFollowingList,
    similarUsersList,
  } = props;
  const { currentUser } = React.useContext(GlobalAppContext);
  const currentUserName = currentUser?.name;

  const renderSimilarUsersList = React.useCallback(() => {
    if (similarUsersList.length === 0) {
      return (
        <>
          <hr />
          <div className="similar-users-empty text-center text-muted">
            Users with similar music tastes to{" "}
            {userName === currentUserName ? "you" : userName} will appear
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
    userName,
    currentUserName,
    loggedInUserFollowsUser,
    updateFollowingList,
  ]);

  return (
    <div data-testid="similar-users-modal">
      <h3 className="text-center" style={{ marginTop: "10px" }}>
        Similar Users
      </h3>
      {renderSimilarUsersList()}
    </div>
  );
}

export default SimilarUsersModal;
