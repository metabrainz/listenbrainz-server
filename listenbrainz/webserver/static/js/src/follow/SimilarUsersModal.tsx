import * as React from "react";
import { includes as _includes } from "lodash";

import Pill from "../components/Pill";
import APIService from "../APIService";
import UserListModalEntry from "./UserListModalEntry";

export type SimilarUsersModalProps = {
  user: ListenBrainzUser;
  loggedInUser: ListenBrainzUser | null;
};

type SimilarUsersModalState = {
  followerList: Array<ListenBrainzUser>;
  similarUsersList: Array<SimilarUser>;
};

export default class SimilarUsersModal extends React.Component<
  SimilarUsersModalProps,
  SimilarUsersModalState
> {
  APIService: APIService;

  constructor(props: SimilarUsersModalProps) {
    super(props);
    this.APIService = new APIService(`${window.location.origin}/1`);
    this.state = {
      followerList: [],
      similarUsersList: [],
    };

    this.getSimilarUsers();
  }

  getSimilarUsers = () => {
    // TODO: implement the API call
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

  loggedInUserFollowsUser = (user: ListenBrainzUser): boolean => {
    const { loggedInUser } = this.props;
    const { followerList } = this.state;

    if (!loggedInUser) {
      return false;
    }

    return _includes(
      followerList.map((listEntry: ListenBrainzUser) => listEntry.name),
      user.name
    );
  };

  render() {
    const { user, loggedInUser } = this.props;
    const { similarUsersList } = this.state;
    return (
      <>
        <div className="text-center follower-following-pills" />
        <h3>
          People similar to{" "}
          {user.name === loggedInUser?.name ? "you" : user.name}
        </h3>
        <div className="follower-following-list">
          {similarUsersList.map((listEntry: SimilarUser) => {
            return (
              <>
                <UserListModalEntry
                  mode="similar-users"
                  key={listEntry.name}
                  user={{ name: listEntry.name }}
                  loggedInUser={loggedInUser}
                  similarityScore={listEntry.similarityScore}
                  loggedInUserFollowsUser={this.loggedInUserFollowsUser(
                    listEntry
                  )}
                />
              </>
            );
          })}
        </div>
      </>
    );
  }
}
