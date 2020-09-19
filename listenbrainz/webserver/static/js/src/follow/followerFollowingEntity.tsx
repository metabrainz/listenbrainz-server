/* eslint-disable react/prefer-stateless-function */
import * as React from "react";
import { includes as _includes } from "lodash";

import Pill from "../components/Pill";
import FollowButton from "../FollowButton";

export type FollowerFollowingEntityProps = {
  user: ListenBrainzUser;
  loggedInUser?: ListenBrainzUser;
  followerList: Array<FollowerFollowingEntityEntry>;
  followingList: Array<FollowerFollowingEntityEntry>;
};

type FollowerFollowingEntityState = {
  mode: FollowerFollowingEntityMode;
  activeModeList: Array<FollowerFollowingEntityEntry>;
};

export default class FollowerFollowingEntity extends React.Component<
  FollowerFollowingEntityProps,
  FollowerFollowingEntityState
> {
  constructor(props: FollowerFollowingEntityProps) {
    super(props);

    this.state = {
      mode: "followers",
      activeModeList: props.followerList,
    };
  }

  updateMode = (mode: FollowerFollowingEntityMode) => {
    const { followerList, followingList } = this.props;
    this.setState({ mode });
    this.setState({
      activeModeList: mode === "followers" ? followerList : followingList,
    });
  };

  loggedInUserFollowsUser = (user: FollowerFollowingEntityEntry): boolean => {
    const { followingList } = this.props;
    return _includes(followingList, user);
  };

  render() {
    const { user, loggedInUser, followerList, followingList } = this.props;
    const { mode, activeModeList } = this.state;
    return (
      <>
        <div className="btn-group btn-group-justified" role="group">
          <Pill
            active={mode === "followers"}
            type="primary"
            onClick={() => this.updateMode("followers")}
          >
            {followerList.length} Followers
          </Pill>
          <Pill
            active={mode === "following"}
            type="primary"
            onClick={() => this.updateMode("following")}
          >
            {followingList.length} Following
          </Pill>
        </div>
        <div className="follower-following-list">
          {activeModeList.map((listentry) => {
            return (
              <>
                <a
                  href={`/user/${listentry.user_name}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {listentry.user_name}
                </a>
                <FollowButton
                  user={{ name: listentry.user_name }}
                  loggedInUser={loggedInUser}
                  loggedInUserFollowsUser={this.loggedInUserFollowsUser(
                    listentry
                  )}
                />
                <hr />
              </>
            );
          })}
        </div>
      </>
    );
  }
}
