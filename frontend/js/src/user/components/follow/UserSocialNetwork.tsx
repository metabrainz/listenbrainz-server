import { isEmpty, isNil, intersectionBy } from "lodash";
import * as React from "react";
import { toast } from "react-toastify";
import Card from "../../../components/Card";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import FollowerFollowingModal from "./FollowerFollowingModal";
import SimilarUsersModal from "./SimilarUsersModal";
import CompatibilityCard from "./CompatibilityCard";
import { ToastMsg } from "../../../notifications/Notifications";

export type UserSocialNetworkProps = {
  user: ListenBrainzUser;
};

export type UserSocialNetworkState = {
  followerList: Array<string>;
  followingList: Array<string>;
  currentUserFollowingList: Array<string>;
  similarUsersList: Array<SimilarUser>;
  similarArtists: Array<{
    artist_name: string;
    artist_mbid: string | null;
    listen_count: number;
  }>;
  similarityScore: number;
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
      currentUserFollowingList: [],
      similarArtists: [],
      similarityScore: 0,
    };
  }

  async componentDidMount() {
    await this.getFollowing();
    await this.getFollowers();
    await this.getSimilarUsers();
    await this.getCurrentUserFollowing();
    await this.getSimilarity();
    await this.getSimilarArtists();
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
      toast.error(
        <ToastMsg
          title=" Error while fetching similar users"
          message={err.toString()}
        />,
        { toastId: "fetch-similar-error" }
      );
    }
  };

  getSimilarity = async () => {
    const { user } = this.props;
    const { APIService, currentUser } = this.context;
    if (currentUser?.name === user?.name) {
      return;
    }
    const { getSimilarityBetweenUsers } = APIService;
    try {
      const response = await getSimilarityBetweenUsers(
        user.name,
        currentUser.name
      );
      const { payload } = response;
      const similarityScore = payload.similarity;
      this.setState({ similarityScore });
    } catch (err) {
      if (err.toString() === "Error: Similar-to user not found") {
        // cannot get similarity if not in the list, so just return 0
        this.setState({ similarityScore: 0 });
      } else {
        toast.error(
          <ToastMsg
            title="Error while fetching similarity"
            message={err.toString()}
          />,
          { toastId: "fetch-similarity-error" }
        );
      }
    }
  };

  getSimilarArtists = async () => {
    const { user } = this.props;
    const { APIService, currentUser } = this.context;
    if (currentUser?.name === user?.name) {
      return;
    }
    const { getUserEntity } = APIService;
    try {
      let response = await getUserEntity(
        user.name,
        "artist",
        "all_time",
        0,
        100
      );
      const userArtists = (response as UserArtistsResponse).payload.artists;
      response = await getUserEntity(
        currentUser.name,
        "artist",
        "all_time",
        0,
        100
      );
      const currentUserArtists = (response as UserArtistsResponse).payload
        .artists;
      let similarArtists = intersectionBy(
        userArtists,
        currentUserArtists,
        "artist_name"
      );
      if (similarArtists.length > 5) {
        similarArtists = similarArtists.slice(0, 5);
      }
      this.setState({ similarArtists });
    } catch (err) {
      toast.error(
        <ToastMsg
          title="Error while fetching user artists"
          message={err.toString()}
        />,
        { toastId: "fetch-artists-error" }
      );
    }
  };

  getFollowers = async () => {
    const { user } = this.props;
    const { APIService } = this.context;
    const { getFollowersOfUser } = APIService;
    try {
      const response = await getFollowersOfUser(user.name);
      const { followers } = response;

      this.setState({ followerList: followers });
    } catch (err) {
      toast.error(
        <ToastMsg
          title="Error while fetching followers"
          message={err.toString()}
        />,
        { toastId: "fetch-followers-error" }
      );
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
      toast.error(
        <ToastMsg
          title={`Error while fetching ${user?.name}'s following`}
          message={err.toString()}
        />,
        { toastId: "fetch-following-error" }
      );
    }
  };

  getCurrentUserFollowing = async () => {
    const { APIService, currentUser } = this.context;
    if (!currentUser?.name) {
      return;
    }
    const { getFollowingForUser } = APIService;
    try {
      const response = await getFollowingForUser(currentUser.name);
      const { following } = response;

      this.setState({ currentUserFollowingList: following });
    } catch (err) {
      toast.error(
        <ToastMsg
          title="Error while fetching the users you follow"
          message={err.toString()}
        />,
        { toastId: "fetch-following-error" }
      );
    }
  };

  loggedInUserFollowsUser = (user: ListenBrainzUser): boolean => {
    const { currentUser } = this.context;
    const { currentUserFollowingList } = this.state;

    if (isNil(currentUser) || isEmpty(currentUser)) {
      return false;
    }

    return currentUserFollowingList.includes(user.name);
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
    const { currentUser } = this.context;
    const {
      followerList,
      followingList,
      similarUsersList,
      similarArtists,
      similarityScore,
    } = this.state;
    return (
      <>
        {currentUser?.name !== user?.name && (
          <CompatibilityCard
            user={user}
            similarityScore={similarityScore}
            similarArtists={similarArtists}
          />
        )}
        <Card className="card-user-sn hidden-xs hidden-sm">
          <FollowerFollowingModal
            user={user}
            followerList={followerList}
            followingList={followingList}
            loggedInUserFollowsUser={this.loggedInUserFollowsUser}
            updateFollowingList={this.updateFollowingList}
          />
        </Card>
        <Card className="card-user-sn hidden-xs hidden-sm">
          <SimilarUsersModal
            user={user}
            similarUsersList={similarUsersList}
            loggedInUserFollowsUser={this.loggedInUserFollowsUser}
            updateFollowingList={this.updateFollowingList}
          />
        </Card>
      </>
    );
  }
}
