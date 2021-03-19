import * as React from "react";

import APIService from "../APIService";
import FollowerFollowingModal from "./FollowerFollowingModal";
import SimilarUsersModal from "./SimilarUsersModal";

export type UserSocialNetworkProps = {
  apiUrl: string;
  user: ListenBrainzUser;
  loggedInUser: ListenBrainzUser | null;
};

type UserSocialNetworkState = {
  followerList: Array<string>;
  followingList: Array<string>;
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
  }

  async componentDidMount() {
    await this.getFollowing();
    await this.getFollowers();
    await this.getSimilarUsers();
  }

  getSimilarUsers = async () => {
    const { user } = this.props;
    try {
      const response = await this.APIService.getSimilarUsersForUser(user.name);
      const { payload } = response;
      const similarUsersList = payload.map((similarUser) => {
        return {
          name: similarUser.user_name,
          similarityScore: similarUser.similarity,
        };
      });
      this.setState({
        similarUsersList,
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error(err);
    }
  };

  getFollowers = async () => {
    const { loggedInUser } = this.props;
    if (!loggedInUser) {
      return;
    }
    try {
      const response = await this.APIService.getFollowersOfUser(
        loggedInUser.name
      );
      const { followers } = response;

      this.setState({ followerList: followers });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error(err);
    }
  };

  getFollowing = async () => {
    const { user } = this.props;
    try {
      const response = await this.APIService.getFollowingForUser(user.name);
      const { following } = response;

      this.setState({ followingList: following });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error(err);
    }
  };

  loggedInUserFollowsUser = (user: ListenBrainzUser): boolean => {
    const { loggedInUser } = this.props;
    const { followingList } = this.state;

    if (!loggedInUser) {
      return false;
    }

    return followingList.includes(user.name);
  };

  updateFollowingList = (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => {
    const { followingList } = this.state;
    const newFollowingList = [...followingList];
    const index = newFollowingList.findIndex(
      (following) => following === user.name
    );
    if (action === "follow" && index === -1) {
      newFollowingList.push(user.name);
    }
    if (action === "unfollow" && index !== -1) {
      newFollowingList.splice(index, 1);
    }
    this.setState({ followingList: newFollowingList });
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
