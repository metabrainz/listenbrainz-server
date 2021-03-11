import * as React from "react";
import { includes as _includes } from "lodash";

import Pill from "../components/Pill";
import APIService from "../APIService";
import UserListModalEntry from "./UserListModalEntry";

export type FollowerFollowingModalProps = {
  user: ListenBrainzUser;
  loggedInUser: ListenBrainzUser | null;
  followerList: Array<ListenBrainzUser>;
  followingList: Array<ListenBrainzUser>;
  loggedInUserFollowsUser: (user: ListenBrainzUser | SimilarUser) => boolean;
  updateFollowingList: (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => void;
};

type FollowerFollowingModalState = {
  activeMode: "follower" | "following";
  followerList: Array<ListenBrainzUser>;
  followingList: Array<ListenBrainzUser>;
  activeModeList: Array<ListenBrainzUser>;
};

export default class FollowerFollowingModal extends React.Component<
  FollowerFollowingModalProps,
  FollowerFollowingModalState
> {
  APIService: APIService;

  constructor(props: FollowerFollowingModalProps) {
    super(props);
    this.APIService = new APIService(`${window.location.origin}/1`);
    this.state = {
      activeMode: "follower",
      followerList: [],
      followingList: [],
      activeModeList: [],
    };
  }

  componentDidUpdate(prevProps: FollowerFollowingModalProps) {
    const { followerList, followingList } = this.props;
    const { activeMode } = this.state;
    // UserSocial will update this prop and we need to update the state accordingly
    if (prevProps.followerList !== followerList) {
      this.setState({
        followerList,
        activeModeList:
          activeMode === "follower" ? followerList : followingList,
      });
    }
    if (prevProps.followingList !== followingList) {
      this.setState({
        followingList,
        activeModeList:
          activeMode === "follower" ? followerList : followingList,
      });
    }
  }

  updateMode = (mode: "follower" | "following") => {
    this.setState({ activeMode: mode }, () => {
      const { activeMode } = this.state;
      const { followerList, followingList } = this.state;
      if (activeMode === "follower") {
        this.setState({ activeModeList: followerList });
      } else {
        this.setState({ activeModeList: followingList });
      }
    });
  };

  render() {
    const {
      loggedInUser,
      loggedInUserFollowsUser,
      updateFollowingList,
    } = this.props;
    const {
      activeMode,
      followerList,
      followingList,
      activeModeList,
    } = this.state;
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
          {activeModeList.map((listEntry: ListenBrainzUser) => {
            return (
              <>
                <UserListModalEntry
                  mode="follow-following"
                  key={listEntry.name}
                  user={{ name: listEntry.name }}
                  loggedInUser={loggedInUser}
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
