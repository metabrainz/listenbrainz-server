/*
 * listenbrainz-server - Server for the ListenBrainz project.
 *
 * Copyright (C) 2020 Param Singh <iliekcomputers@gmail.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

import * as React from "react";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faUserCheck,
  faUserPlus,
  faUserTimes,
  faExclamationTriangle,
} from "@fortawesome/free-solid-svg-icons";
import GlobalAppContext from "../../../utils/GlobalAppContext";

type FollowButtonProps = {
  type: "icon-only" | "block" | string;
  user: ListenBrainzUser;
  loggedInUserFollowsUser: boolean;
  updateFollowingList?: (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => void;
};

type FollowButtonState = {
  loggedInUserFollowsUser: boolean;
  justFollowed: boolean;
  hover: boolean;
  error: boolean;
};

class FollowButton extends React.Component<
  FollowButtonProps,
  FollowButtonState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: FollowButtonProps) {
    super(props);
    this.state = {
      loggedInUserFollowsUser: props.loggedInUserFollowsUser,
      hover: false,
      justFollowed: false,
      error: false,
    };
  }

  componentDidUpdate(prevProps: FollowButtonProps) {
    const { loggedInUserFollowsUser } = this.props;
    // FollowerFollowingModal will update this prop and we need to update the state accordingly
    if (prevProps.loggedInUserFollowsUser !== loggedInUserFollowsUser) {
      this.setState({ loggedInUserFollowsUser });
    }
  }

  setHover = (value: boolean) => {
    this.setState({ hover: value, justFollowed: false });
  };

  handleButtonClick = () => {
    const { loggedInUserFollowsUser } = this.state;
    if (loggedInUserFollowsUser) {
      this.unfollowUser();
    } else {
      this.followUser();
    }
  };

  followUser = () => {
    const { user, updateFollowingList } = this.props;
    const { APIService, currentUser } = this.context;
    const { followUser } = APIService;

    followUser(user.name, currentUser?.auth_token!).then(({ status }) => {
      if (status === 200) {
        this.setState({ loggedInUserFollowsUser: true, justFollowed: true });
        if (updateFollowingList) {
          updateFollowingList(user, "follow");
        }
      } else {
        this.setState({ error: true });
      }
    });
  };

  unfollowUser = () => {
    const { user, updateFollowingList } = this.props;
    const { APIService, currentUser } = this.context;
    const { unfollowUser } = APIService;

    unfollowUser(user.name, currentUser?.auth_token!).then(({ status }) => {
      if (status === 200) {
        this.setState({
          loggedInUserFollowsUser: false,
          justFollowed: false,
        });
        if (updateFollowingList) {
          updateFollowingList(user, "unfollow");
        }
      } else {
        this.setState({ error: true });
      }
    });
  };

  getButtonDetails = (): {
    buttonIcon: IconProp;
    buttonClass?: string;
    buttonText: string;
  } => {
    const { error, justFollowed, loggedInUserFollowsUser, hover } = this.state;

    if (error) {
      return {
        buttonIcon: faExclamationTriangle as IconProp,
        buttonText: "Error!!",
      };
    }

    if (justFollowed) {
      return {
        buttonIcon: faUserCheck as IconProp,
        buttonText: "Following",
      };
    }

    if (loggedInUserFollowsUser) {
      if (!hover) {
        return {
          buttonIcon: faUserCheck as IconProp,
          buttonClass: "following",
          buttonText: "Following",
        };
      }
      return {
        buttonIcon: faUserTimes as IconProp,
        buttonClass: "following",
        buttonText: "Unfollow",
      };
    }

    return {
      buttonIcon: faUserPlus as IconProp,
      buttonText: "Follow",
    };
  };

  render() {
    const { type } = this.props;
    const { buttonClass, buttonText, buttonIcon } = this.getButtonDetails();
    return (
      <button
        onClick={this.handleButtonClick}
        onKeyPress={this.handleButtonClick}
        onMouseEnter={() => this.setHover(true)}
        onMouseLeave={() => this.setHover(false)}
        className={`lb-follow-button btn btn-sm ${buttonClass} ${type}`}
        type="button"
        tabIndex={0}
      >
        <FontAwesomeIcon icon={buttonIcon} />
        <div className="text">{buttonText}</div>
      </button>
    );
  }
}

export default FollowButton;
