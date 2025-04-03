import { isEmpty, isNil, intersectionBy } from "lodash";
import * as React from "react";
import { toast } from "react-toastify";
import Card from "../../../components/Card";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import FollowerFollowingModal from "./FollowerFollowingModal";
import SimilarUsersModal from "./SimilarUsersModal";
import CompatibilityCard from "./CompatibilityCard";
import { ToastMsg } from "../../../notifications/Notifications";
import FlairsExplanationButton from "../../../common/flairs/FlairsExplanationButton";
import useUserFlairs from "../../../utils/FlairLoader";

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

  async componentDidUpdate(prevProps: UserSocialNetworkProps) {
    const { user: currentUser } = this.props;
    if (prevProps.user.name !== currentUser.name) {
      await this.getFollowing();
      await this.getFollowers();
      await this.getSimilarUsers();
      await this.getCurrentUserFollowing();
      await this.getSimilarity();
      await this.getSimilarArtists();
    }
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
    if (
      isNil(currentUser) ||
      isEmpty(currentUser) ||
      currentUser?.name === user?.name
    ) {
      return;
    }
    const { getSimilarityBetweenUsers } = APIService;
    try {
      const response = await getSimilarityBetweenUsers(
        currentUser.name,
        user.name
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
    if (
      isNil(currentUser) ||
      isEmpty(currentUser) ||
      currentUser?.name === user?.name
    ) {
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
      const similarArtists = intersectionBy(
        userArtists,
        currentUserArtists,
        "artist_name"
      );
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
    const { currentUser } = this.context;
    const { user: profileUser } = this.props;
    const { followingList, currentUserFollowingList } = this.state;

    if (!currentUser) return;

    // update the logged-in user's following list (for similar users pane)
    const newCurrentUserFollowingList = [...currentUserFollowingList];
    const currentUserIndex = newCurrentUserFollowingList.indexOf(user.name);

    if (action === "follow" && currentUserIndex === -1) {
      newCurrentUserFollowingList.push(user.name);
    } else if (action === "unfollow" && currentUserIndex !== -1) {
      newCurrentUserFollowingList.splice(currentUserIndex, 1);
    }

    // update the users following list (for followers/following pane)
    const newFollowingList = [...followingList];
    if (profileUser.name === currentUser.name) {
      const profileUserIndex = newFollowingList.indexOf(user.name);
      if (action === "follow" && profileUserIndex === -1) {
        newFollowingList.push(user.name);
      } else if (action === "unfollow" && profileUserIndex !== -1) {
        newFollowingList.splice(profileUserIndex, 1);
      }
    }

    // Update both lists in state
    this.setState({
      followingList: newFollowingList,
      currentUserFollowingList: newCurrentUserFollowingList,
    });
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
    const isAnotherUser =
      Boolean(currentUser?.name) && currentUser.name !== user?.name;
    return (
      <>
        {isAnotherUser && (
          <CompatibilityCard
            user={user}
            similarityScore={similarityScore}
            similarArtists={similarArtists}
          />
        )}
        <Card className="hidden-xs">
          <FollowerFollowingModal
            user={user}
            followerList={followerList}
            followingList={followingList}
            loggedInUserFollowsUser={this.loggedInUserFollowsUser}
            updateFollowingList={this.updateFollowingList}
          />
        </Card>
        {isAnotherUser && <FlairsExplanationButton className="hidden-xs" />}
        <Card className="mt-15 card-user-sn hidden-xs">
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
