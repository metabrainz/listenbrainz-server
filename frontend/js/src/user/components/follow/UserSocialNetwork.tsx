import * as React from "react";
import { isEmpty, isNil, intersectionBy } from "lodash";
import { toast } from "react-toastify";
import Card from "../../../components/Card";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import FollowerFollowingModal from "./FollowerFollowingModal";
import SimilarUsersModal from "./SimilarUsersModal";
import CompatibilityCard from "./CompatibilityCard";
import { ToastMsg } from "../../../notifications/Notifications";
import FlairsExplanationButton from "../../../common/flairs/FlairsExplanationButton";

export type UserSocialNetworkProps = {
  user: ListenBrainzUser;
};

function UserSocialNetwork(props: UserSocialNetworkProps) {
  const { user: profileUser } = props;
  const { currentUser, APIService } = React.useContext(GlobalAppContext);

  const [followerList, setFollowerList] = React.useState<Array<string>>([]);
  const [followingList, setFollowingList] = React.useState<Array<string>>([]);
  const [
    currentUserFollowingList,
    setCurrentUserFollowingList,
  ] = React.useState<Array<string>>([]);
  const [similarUsersList, setSimilarUsersList] = React.useState<
    Array<SimilarUser>
  >([]);
  const [similarArtists, setSimilarArtists] = React.useState<
    Array<{
      artist_name: string;
      artist_mbid: string | null;
      listen_count: number;
    }>
  >([]);
  const [similarityScore, setSimilarityScore] = React.useState<number>(0);

  React.useEffect(() => {
    const {
      getFollowersOfUser,
      getFollowingForUser,
      getSimilarUsersForUser,
      getSimilarityBetweenUsers,
      getUserEntity,
    } = APIService;

    // Get followers
    getFollowersOfUser(profileUser.name)
      .then((response: { followers: string[] }) => {
        setFollowerList(response.followers || []);
      })
      .catch((err: Error) => {
        toast.error(
          <ToastMsg
            title="Error while fetching followers"
            message={err.toString()}
          />,
          { toastId: "fetch-followers-error" }
        );
      });

    // Get following
    getFollowingForUser(profileUser.name)
      .then((response: { following: string[] }) => {
        setFollowingList(response.following || []);
      })
      .catch((err: Error) => {
        toast.error(
          <ToastMsg
            title={`Error while fetching ${profileUser?.name}'s following`}
            message={err.toString()}
          />,
          { toastId: "fetch-following-error" }
        );
      });

    // Get similar users
    getSimilarUsersForUser(profileUser.name)
      .then(
        (response: {
          payload: Array<{ user_name: string; similarity: number }>;
        }) => {
          const { payload } = response;
          setSimilarUsersList(
            payload.map((similarUser) => ({
              name: similarUser.user_name,
              similarityScore: similarUser.similarity,
            }))
          );
        }
      )
      .catch((err: Error) => {
        toast.error(
          <ToastMsg
            title=" Error while fetching similar users"
            message={err.toString()}
          />,
          { toastId: "fetch-similar-error" }
        );
      });

    // Get current user following (only if logged in)
    if (currentUser?.name) {
      getFollowingForUser(currentUser.name)
        .then((response: { following: string[] }) => {
          setCurrentUserFollowingList(response.following || []);
        })
        .catch((err: Error) => {
          toast.error(
            <ToastMsg
              title="Error while fetching the users you follow"
              message={err.toString()}
            />,
            { toastId: "fetch-following-error" }
          );
        });
    }

    // Get similarity and similar artists (only if logged in and different user)
    if (currentUser?.name && currentUser.name !== profileUser.name) {
      // Get similarity
      getSimilarityBetweenUsers(currentUser.name, profileUser.name)
        .then((response: { payload: { similarity: number } }) => {
          setSimilarityScore(response.payload.similarity);
        })
        .catch((err: Error) => {
          if (err.toString() !== "Error: Similar-to user not found") {
            toast.error(
              <ToastMsg
                title="Error while fetching similarity"
                message={err.toString()}
              />,
              { toastId: "fetch-similarity-error" }
            );
          }
        });

      // Get similar artists
      Promise.all([
        getUserEntity(profileUser.name, "artist", "all_time", 0, 100),
        getUserEntity(currentUser.name, "artist", "all_time", 0, 100),
      ])
        .then(([userResponse, currentUserResponse]) => {
          const userArtists = (userResponse as UserArtistsResponse).payload
            .artists;
          const currentUserArtists = (currentUserResponse as UserArtistsResponse)
            .payload.artists;
          setSimilarArtists(
            intersectionBy(userArtists, currentUserArtists, "artist_name")
          );
        })
        .catch((err: Error) => {
          toast.error(
            <ToastMsg
              title="Error while fetching user artists"
              message={err.toString()}
            />,
            { toastId: "fetch-artists-error" }
          );
        });
    }
  }, [profileUser, currentUser, APIService]);

  const isAnotherUser =
    Boolean(currentUser?.name) && currentUser.name !== profileUser?.name;

  const loggedInUserFollowsUser = (user: ListenBrainzUser): boolean => {
    if (isNil(currentUser) || isEmpty(currentUser)) {
      return false;
    }

    return currentUserFollowingList.includes(user.name);
  };

  const updateFollowingList = (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => {
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
    // setFollowingList(newFollowingList);
    // setCurrentUserFollowingList(newCurrentUserFollowingList);
  };

  return (
    <>
      {isAnotherUser && (
        <CompatibilityCard
          user={profileUser}
          similarityScore={similarityScore}
          similarArtists={similarArtists}
        />
      )}
      <Card className="d-none d-md-block">
        <FollowerFollowingModal
          user={profileUser}
          followerList={followerList}
          followingList={followingList}
          loggedInUserFollowsUser={loggedInUserFollowsUser}
          updateFollowingList={updateFollowingList}
        />
      </Card>
      {isAnotherUser && (
        <FlairsExplanationButton className="d-none d-md-block" />
      )}
      <Card className="mt-4 card-user-sn d-none d-md-block">
        <SimilarUsersModal
          user={profileUser}
          similarUsersList={similarUsersList}
          loggedInUserFollowsUser={loggedInUserFollowsUser}
          updateFollowingList={updateFollowingList}
        />
      </Card>
    </>
  );
}

export default UserSocialNetwork;
