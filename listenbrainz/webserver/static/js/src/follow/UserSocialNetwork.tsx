import * as React from "react";
import { includes as _includes } from "lodash";

import APIService from "../APIService";
import FollowerFollowingModal from "./FollowerFollowingModal";
import SimilarUsersModal from "./SimilarUsersModal";

export type UserSocialNetworkProps = {
  apiUrl: string;
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
    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );
    this.state = {
      followerList: [],
      followingList: [],
      similarUsersList: [],
    };

    this.getFollowing();
    this.getFollowers();
    this.getSimilarUsers();
  }

  getSimilarUsers = () => {
    const { user } = this.props;

    this.APIService.getSimilarUsersForUser(user.name)
      .then(
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
                };
              }
            ),
          });
        }
      )
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.error(err);
      });
  };

  getFollowers = () => {
    const { loggedInUser } = this.props;
    if (!loggedInUser) {
      return;
    }

    this.APIService.getFollowersOfUser(loggedInUser.name)
      .then(
        ({ followers }: { followers: Array<{ musicbrainz_id: string }> }) => {
          this.setState({
            followerList: followers.map(({ musicbrainz_id }) => {
              return {
                name: musicbrainz_id,
              };
            }),
          });
        }
      )
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.error(err);
      });
  };

  getFollowing = () => {
    const { user } = this.props;
    this.APIService.getFollowingForUser(user.name)
      .then(
        ({ following }: { following: Array<{ musicbrainz_id: string }> }) => {
          this.setState({
            followingList: following.map(({ musicbrainz_id }) => {
              return { name: musicbrainz_id };
            }),
          });
        }
      )
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.error(err);
      });
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
