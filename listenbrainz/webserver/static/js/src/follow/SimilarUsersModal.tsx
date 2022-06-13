import * as React from "react";
import { includes as _includes } from "lodash";

import UserListModalEntry from "./UserListModalEntry";
import GlobalAppContext from "../utils/GlobalAppContext";

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
      <h3 className="text-center" style={{ marginTop: "10px" }}>
        Similar Users
      </h3>
      {similarUsersList.length === 0 ? (
        <>
          <hr style={{ margin: "0px 2em", borderTop: "1px solid #eee" }} />
          <div className="similar-users-empty text-center text-muted">
            Users with similar music tastes to{" "}
            {user.name === currentUser?.name ? "you" : user.name} will appear
            here.
          </div>
        </>
      ) : (
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
      )}
    </>
  );
};

export default SimilarUsersModal;
