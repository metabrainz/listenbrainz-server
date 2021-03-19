import * as React from "react";
import { includes as _includes } from "lodash";

import Pill from "../components/Pill";
import UserListModalEntry from "./UserListModalEntry";

export type FollowerFollowingModalProps = {
  user: ListenBrainzUser;
  loggedInUser: ListenBrainzUser | null;
  followerList: Array<string>;
  followingList: Array<string>;
  loggedInUserFollowsUser: (user: ListenBrainzUser | SimilarUser) => boolean;
  updateFollowingList: (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => void;
};

type FollowerFollowingModalState = {
  activeMode: "follower" | "following";
};

export default class FollowerFollowingModal extends React.Component<
  FollowerFollowingModalProps,
  FollowerFollowingModalState
> {
  constructor(props: FollowerFollowingModalProps) {
    super(props);
    this.state = {
      activeMode: "follower",
    };
  }

  updateMode = (mode: "follower" | "following") => {
    this.setState({ activeMode: mode });
  };

  render() {
    const {
      loggedInUser,
      loggedInUserFollowsUser,
      updateFollowingList,
      followerList,
      followingList,
    } = this.props;
    const { activeMode } = this.state;

    const activeModeList =
      activeMode === "follower" ? followerList : followingList;
    return (
      <>
        <div className="text-center follower-following-pills">
          <div className="btn-group btn-group-justified" role="group">
            <Pill
              active={activeMode === "follower"}
              type="secondary"
              onClick={() => this.updateMode("follower")}
            >
              Followers ({followerList.length})
            </Pill>
            <Pill
              active={activeMode === "following"}
              type="secondary"
              onClick={() => this.updateMode("following")}
            >
              Following ({followingList.length})
            </Pill>
          </div>
        </div>
        <div className="follower-following-list">
          {activeModeList.map((listEntry: string) => {
            const formattedAsUser: ListenBrainzUser = {
              name: listEntry,
            };
            return (
              <UserListModalEntry
                mode="follow-following"
                key={listEntry}
                user={formattedAsUser}
                loggedInUser={loggedInUser}
                loggedInUserFollowsUser={loggedInUserFollowsUser(
                  formattedAsUser
                )}
                updateFollowingList={updateFollowingList}
              />
            );
          })}
        </div>
      </>
    );
  }
}
