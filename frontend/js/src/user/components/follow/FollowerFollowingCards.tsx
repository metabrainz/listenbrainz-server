import * as React from "react";
import { includes as _includes } from "lodash";

import Pill from "../../../components/Pill";
import UserListModalEntry from "./UserListModalEntry";
import GlobalAppContext from "../../../utils/GlobalAppContext";

export type FollowerFollowingCardsProps = {
  userName: string;
  followerList: Array<string>;
  followingList: Array<string>;
  loggedInUserFollowsUser: (user: ListenBrainzUser | SimilarUser) => boolean;
  updateFollowingList: (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => void;
};

type FollowerFollowingCardsState = {
  activeMode: "follower" | "following";
};

export default class FollowerFollowingCards extends React.Component<
  FollowerFollowingCardsProps,
  FollowerFollowingCardsState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: FollowerFollowingCardsProps) {
    super(props);
    this.state = {
      activeMode: "following",
    };
  }

  updateMode = (mode: "follower" | "following") => {
    this.setState({ activeMode: mode });
  };

  render() {
    const {
      loggedInUserFollowsUser,
      updateFollowingList,
      followerList,
      followingList,
      userName,
    } = this.props;
    const { activeMode } = this.state;
    const { currentUser } = this.context;

    const activeModeList =
      activeMode === "follower" ? followerList : followingList;

    function renderFollowerFollowingList() {
      if (activeModeList.length === 0) {
        if (activeMode === "follower") {
          return (
            <>
              <hr />
              <div className="follower-following-empty text-center text-muted">
                {userName === currentUser?.name
                  ? "You don't"
                  : `${userName} doesn't`}{" "}
                have any followers.
              </div>
            </>
          );
        }
        return (
          <>
            <hr />
            <div className="follower-following-empty text-center text-muted">
              {userName === currentUser?.name
                ? "You aren't"
                : `${userName} isn't`}{" "}
              following anyone.
            </div>
          </>
        );
      }
      return (
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
                loggedInUserFollowsUser={loggedInUserFollowsUser(
                  formattedAsUser
                )}
                updateFollowingList={updateFollowingList}
              />
            );
          })}
        </div>
      );
    }

    return (
      <div data-testid="follower-following-cards">
        <div className="text-center follower-following-pills py-3">
          <div className="btn-group center-block" role="group">
            <Pill
              className="mx-2 my-0"
              active={activeMode === "follower"}
              type="secondary"
              onClick={() => this.updateMode("follower")}
            >
              Followers ({followerList.length})
            </Pill>
            <Pill
              className="mx-2 my-0"
              active={activeMode === "following"}
              type="secondary"
              onClick={() => this.updateMode("following")}
            >
              Following ({followingList.length})
            </Pill>
          </div>
        </div>
        {renderFollowerFollowingList()}
      </div>
    );
  }
}
