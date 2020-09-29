import * as React from "react";
import { includes as _includes } from "lodash";

import Pill from "../components/Pill";
import FollowButton from "../FollowButton";
import APIService from "../APIService";

export type FollowerFollowingModalProps = {
  user: ListenBrainzUser;
};

type FollowerFollowingModalState = {
  activeMode: "follower" | "following";
  followerList: Array<ListenBrainzUser>;
  followingList: Array<ListenBrainzUser>;
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
    };
    this.getFollowers();
    this.getFollowing();
  }

  getFollowers = () => {
    const { user } = this.props;
    this.APIService.getFollowersOfUser(user.name).then(
      ({ followers }: { followers: Array<{ musicbrainz_id: string }> }) => {
        this.setState({
          followerList: followers.map(({ musicbrainz_id }) => {
            return {
              name: musicbrainz_id,
            };
          }),
        });
      }
    );
  };

  getFollowing = () => {
    const { user } = this.props;
    this.APIService.getFollowingForUser(user.name).then(
      ({ following }: { following: Array<{ musicbrainz_id: string }> }) => {
        this.setState({
          followingList: following.map(({ musicbrainz_id }) => {
            return { name: musicbrainz_id };
          }),
        });
      }
    );
  };

  updateMode = (mode: "follower" | "following") => {
    this.setState({ activeMode: mode });
  };

  loggedInUserFollowsUser = (user: ListenBrainzUser): boolean => {
    const { followingList } = this.state;
    return _includes(followingList, user);
  };

  render() {
    const { user } = this.props;
    const { activeMode, followerList, followingList } = this.state;
    const activeModeList =
      activeMode === "follower" ? followerList : followingList;
    return (
      <>
        <div className="btn-group btn-group-justified" role="group">
          <Pill
            active={activeMode === "follower"}
            type="primary"
            onClick={() => this.updateMode("follower")}
          >
            {followerList.length} Followers
          </Pill>
          <Pill
            active={activeMode === "following"}
            type="primary"
            onClick={() => this.updateMode("following")}
          >
            {followingList.length} Following
          </Pill>
        </div>
        <div className="follower-following-list">
          {activeModeList.map((listEntry: ListenBrainzUser) => {
            return (
              <>
                <a
                  href={`/user/${listEntry.name}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {listEntry.name}
                </a>
                <FollowButton
                  user={{ name: listEntry.name }}
                  loggedInUser={user}
                  loggedInUserFollowsUser={this.loggedInUserFollowsUser(
                    listEntry
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
