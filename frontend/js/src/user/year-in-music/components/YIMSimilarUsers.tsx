import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { toPairs } from "lodash";
import React from "react";
import Tooltip from "react-tooltip";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import UserListModalEntry, {
  UserListModalEntryProps,
} from "../../components/follow/UserListModalEntry";

type YIMSimilarUsersProps = {
  similarUsers: { [key: string]: number };
  userName: string;
  updateFollowingList: UserListModalEntryProps["updateFollowingList"];
  loggedInUserFollowsUser: (user: SimilarUser) => boolean;
  year: number;
};
export default function YIMSimilarUsers({
  similarUsers,
  userName,
  updateFollowingList,
  loggedInUserFollowsUser,
  year,
}: YIMSimilarUsersProps) {
  const { currentUser } = React.useContext(GlobalAppContext);
  const isCurrentUser = userName === currentUser?.name;
  const youOrUsername = isCurrentUser ? "you" : `${userName}`;
  const sortedSimilarUsers = React.useMemo(
    () => toPairs(similarUsers).sort((a, b) => b[1] - a[1]),
    [similarUsers]
  );
  if (!sortedSimilarUsers || sortedSimilarUsers.length === 0) {
    return null;
  }
  return (
    <div
      className="content-card"
      id="similar-users"
      style={{ paddingBottom: "4.5em" }}
    >
      <div className="heading">
        <h3>
          Music buddies{" "}
          <FontAwesomeIcon
            icon={faQuestionCircle}
            data-tip
            data-for="music-buddies-helptext"
            size="xs"
          />
          <Tooltip id="music-buddies-helptext">
            Here are the users with the most similar taste to {youOrUsername} in{" "}
            {year}.
            <br />
            Maybe check them out and follow them?
          </Tooltip>
        </h3>
      </div>
      <div className="scrollable-area similar-users-list card-bg">
        {sortedSimilarUsers.map((userFromList) => {
          const [name, similarityScore] = userFromList;
          const similarUser: SimilarUser = {
            name,
            similarityScore,
          };
          const loggedInUserFollows = loggedInUserFollowsUser(similarUser);
          return (
            <UserListModalEntry
              mode="similar-users"
              key={name}
              user={similarUser}
              loggedInUserFollowsUser={loggedInUserFollows}
              updateFollowingList={updateFollowingList}
            />
          );
        })}
      </div>
    </div>
  );
}
