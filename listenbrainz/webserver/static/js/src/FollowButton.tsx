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
import APIService from "./APIService";

type FollowButtonProps = {
  type: "icon-only" | "block";
  user: ListenBrainzUser;
  loggedInUser?: ListenBrainzUser;
  loggedInUserFollowsUser: boolean;
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
  APIService: APIService;

  constructor(props: FollowButtonProps) {
    super(props);
    this.state = {
      loggedInUserFollowsUser: props.loggedInUserFollowsUser,
      hover: false,
      justFollowed: false,
      error: false,
    };

    this.APIService = new APIService(`${window.location.origin}/1`);
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
    const { user } = this.props;
    this.APIService.followUser(user.name).then(({ status }) => {
      if (status === 200) {
        this.setState({ loggedInUserFollowsUser: true, justFollowed: true });
      } else {
        this.setState({ error: true });
      }
    });
  };

  unfollowUser = () => {
    const { user } = this.props;
    this.APIService.unfollowUser(user.name).then(({ status }) => {
      if (status === 200) {
        this.setState({ loggedInUserFollowsUser: false, justFollowed: false });
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
      <div
        onClick={this.handleButtonClick}
        onKeyPress={this.handleButtonClick}
        onMouseEnter={() => this.setHover(true)}
        onMouseLeave={() => this.setHover(false)}
        className={`follow-button btn btn-sm ${buttonClass} ${type}`}
        role="button"
        tabIndex={0}
      >
        <FontAwesomeIcon icon={buttonIcon} />
        <div className="text">{buttonText}</div>
      </div>
    );
  }
}

export default FollowButton;
