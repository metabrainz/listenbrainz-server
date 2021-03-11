import * as React from "react";
import { includes as _includes } from "lodash";

import APIService from "../APIService";
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

type SimilarUsersModalState = {
  similarUsersList: Array<SimilarUser>;
};

export default class SimilarUsersModal extends React.Component<
  SimilarUsersModalProps,
  SimilarUsersModalState
> {
  APIService: APIService;

  constructor(props: SimilarUsersModalProps) {
    super(props);
    this.APIService = new APIService(`${window.location.origin}/1`);
    this.state = {
      similarUsersList: [],
    };
  }

  componentDidUpdate(prevProps: SimilarUsersModalProps) {
    const { similarUsersList } = this.props;

    // UserSocial will update this prop and we need to update the state accordingly
    if (prevProps.similarUsersList !== similarUsersList) {
      this.setState({ similarUsersList });
    }
  }

  render() {
    const {
      user,
      loggedInUser,
      loggedInUserFollowsUser,
      updateFollowingList,
    } = this.props;
    const { similarUsersList } = this.state;
    return (
      <>
        <div className="text-center follower-following-pills" />
        <h3 className="text-center">
          People similar to{" "}
          {user.name === loggedInUser?.name ? "you" : user.name}
        </h3>
        <div className="similar-users-list">
          {similarUsersList.map((listEntry: SimilarUser) => {
            return (
              <>
                <UserListModalEntry
                  mode="similar-users"
                  key={listEntry.name}
                  user={{ name: listEntry.name }}
                  loggedInUser={loggedInUser}
                  similarityScore={listEntry.similarityScore}
                  loggedInUserFollowsUser={loggedInUserFollowsUser(listEntry)}
                  updateFollowingList={updateFollowingList}
                />
              </>
            );
          })}
        </div>
      </>
    );
  }
}
