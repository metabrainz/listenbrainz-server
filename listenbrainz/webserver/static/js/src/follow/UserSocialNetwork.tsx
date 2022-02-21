import { isEmpty, isNil } from "lodash";
import * as React from "react";

import GlobalAppContext from "../utils/GlobalAppContext";
import FollowerFollowingModal from "./FollowerFollowingModal";
import SimilarUsersModal from "./SimilarUsersModal";

export type UserSocialNetworkProps = {
  user: ListenBrainzUser;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
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
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: UserSocialNetworkProps) {
    super(props);
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
    const { APIService } = this.context;
    const { getSimilarUsersForUser } = APIService;
    try {
      const response = await getSimilarUsersForUser(user.name);
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
      const { newAlert } = this.props;
      newAlert("danger", "Error while fetching followers", err.toString());
    }
  };

  getFollowers = async () => {
    const { APIService, currentUser } = this.context;
    const { getFollowersOfUser } = APIService;
    if (isNil(currentUser) || isEmpty(currentUser)) {
      return;
    }
    try {
      const response = await getFollowersOfUser(currentUser.name);
      const { followers } = response;

      this.setState({ followerList: followers });
    } catch (err) {
      const { newAlert } = this.props;
      newAlert("danger", "Error while fetching followers", err.toString());
    }
  };

  getFollowing = async () => {
    const { user } = this.props;
    const { APIService } = this.context;
    const { getFollowingForUser } = APIService;
    try {
      const response = await getFollowingForUser(user.name);
      const { following } = response;

      this.setState({ followingList: following });
    } catch (err) {
      const { newAlert } = this.props;
      newAlert("danger", "Error while fetching followers", err.toString());
    }
  };

  loggedInUserFollowsUser = (user: ListenBrainzUser): boolean => {
    const { currentUser } = this.context;
    const { followingList } = this.state;

    if (isNil(currentUser) || isEmpty(currentUser)) {
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
    const { user } = this.props;
    const { followerList, followingList, similarUsersList } = this.state;
    return (
      <>
        <FollowerFollowingModal
          user={user}
          followerList={followerList}
          followingList={followingList}
          loggedInUserFollowsUser={this.loggedInUserFollowsUser}
          updateFollowingList={this.updateFollowingList}
        />
        <SimilarUsersModal
          user={user}
          similarUsersList={similarUsersList}
          loggedInUserFollowsUser={this.loggedInUserFollowsUser}
          updateFollowingList={this.updateFollowingList}
        />
      </>
    );
  }
}
