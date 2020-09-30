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

    // DO NOT CHANGE THIS ORDER
    // Otherwise react messes up the follow button props;
    // The way to fix this is to not pass the loggedInUserFollowsUser prop
    // into the FollowButton compoent.
    // TODO: fix this
    this.getFollowing();
    this.getFollowers();
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
    this.setState({ activeMode: mode }, () => {
      const { activeMode } = this.state;
      if (activeMode === "follower") this.getFollowers();
      else this.getFollowing();
    });
  };

  loggedInUserFollowsUser = (user: ListenBrainzUser): boolean => {
    const { followingList } = this.state;
    return _includes(
      followingList.map((listEntry: ListenBrainzUser) => listEntry.name),
      user.name
    );
  };

  render() {
    const { user } = this.props;
    const { activeMode, followerList, followingList } = this.state;
    const activeModeList =
      activeMode === "follower" ? followerList : followingList;
    return (
      <>
        <div className="text-center">
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
        <hr />
        <div className="follower-following-list">
          {activeModeList.map((listEntry: ListenBrainzUser) => {
            return (
              <div className="text-center" key={listEntry.name}>
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
              </div>
            );
          })}
        </div>
      </>
    );
  }
}
