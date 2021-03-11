import * as React from "react";
import { includes as _includes } from "lodash";

import APIService from "../APIService";
import UserListModalEntry from "./UserListModalEntry";
import FollowerFollowingModal from "./FollowerFollowingModal";
import SimilarUsersModal from "./SimilarUsersModal";

export type UserSocialNetworkProps = {
  user: ListenBrainzUser;
  loggedInUser: ListenBrainzUser | null;
};

type UserSocialNetworkState = {
  followerList: Array<ListenBrainzUser>;
  followingList: Array<ListenBrainzUser>;
  similarUsersList: Array<SimilarUser>;
};

export default class UserSocialNetwork extends React.Component<
  UserSocialNetworkProps,
  UserSocialNetworkState
> {
  APIService: APIService;

  constructor(props: UserSocialNetworkProps) {
    super(props);
    this.APIService = new APIService(`${window.location.origin}/1`);
    this.state = {
      followerList: [],
      followingList: [],
      similarUsersList: [],
    };

    // DO NOT CHANGE THIS ORDER
    // Otherwise react messes up the follow button props;
    // The way to fix this is to not pass the loggedInUserFollowsUser prop
    // into the FollowButton compoent.
    // TODO: fix this
    this.getFollowing();
    this.getFollowers();
    this.getSimilarUsers();
  }

  getSimilarUsers = () => {
    const { user } = this.props;

    this.APIService.getSimilarUsersForUser(user.name).then(
      ({
        payload,
      }: {
        payload: Array<{ user_name: string; similarity: number }>;
      }) => {
        this.setState({
          similarUsersList: payload.map(
            (similarUser: { user_name: string; similarity: number }) => {
              return {
                name: similarUser.user_name,
                similarityScore: similarUser.similarity,
              } as SimilarUser;
            }
          ),
        });
      }
    );
  };

  getFollowers = () => {
    const { loggedInUser } = this.props;
    if (!loggedInUser) {
      return;
    }

    this.APIService.getFollowersOfUser(loggedInUser.name).then(
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

  loggedInUserFollowsUser = (user: ListenBrainzUser): boolean => {
    const { loggedInUser } = this.props;
    const { followingList } = this.state;

    if (!loggedInUser) {
      return false;
    }

    return _includes(
      followingList.map(
        (listEntry: ListenBrainzUser | SimilarUser) => listEntry.name
      ),
      user.name
    );
  };

  updateFollowingList = (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => {
    const { followingList } = this.state;
    if (action === "follow") {
      followingList.push(user);
    } else {
      const index = followingList.indexOf(user);

      followingList.splice(index, 1);
    }
    this.setState({ followingList });
  };

  render() {
    const { user, loggedInUser } = this.props;
    const { followerList, followingList, similarUsersList } = this.state;
    return (
      <>
        <FollowerFollowingModal
          user={user}
          loggedInUser={loggedInUser}
          followerList={followerList}
          followingList={followingList}
          loggedInUserFollowsUser={this.loggedInUserFollowsUser}
          updateFollowingList={this.updateFollowingList}
        />
        <SimilarUsersModal
          user={user}
          loggedInUser={loggedInUser}
          similarUsersList={similarUsersList}
          loggedInUserFollowsUser={this.loggedInUserFollowsUser}
          updateFollowingList={this.updateFollowingList}
        />
      </>
    );
  }
}
