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
import APIService from "./APIService";

type FollowButtonProps = {
  user: ListenBrainzUser;
  loggedInUser: ListenBrainzUser;
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

  toggleHover = () => {
    const { hover } = this.state;
    this.setState({ hover: !hover, justFollowed: false });
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
    const { loggedInUser, user } = this.props;
    this.APIService.followUser(user.name).then(({ status }) => {
      if (status === 200) {
        this.setState({ loggedInUserFollowsUser: true, justFollowed: true });
      } else {
        this.setState({ error: true });
      }
    });
  };

  unfollowUser = () => {
    const { loggedInUser, user } = this.props;
    this.APIService.unfollowUser(user.name).then(({ status }) => {
      if (status === 200) {
        this.setState({ loggedInUserFollowsUser: false, justFollowed: false });
      } else {
        this.setState({ error: true });
      }
    });
  };

  getButtonDetails = (): { buttonClass: string; buttonText: string } => {
    const { error, justFollowed, loggedInUserFollowsUser, hover } = this.state;

    if (error) {
      return {
        buttonClass: "btn btn-sm btn-danger",
        buttonText: "Something went wrong!",
      };
    }

    if (justFollowed) {
      return { buttonClass: "btn btn-sm btn-info", buttonText: "Following" };
    }

    if (loggedInUserFollowsUser) {
      if (!hover) {
        return { buttonClass: "btn btn-sm btn-info", buttonText: "Following" };
      }
      return { buttonClass: "btn btn-sm btn-danger", buttonText: "Unfollow" };
    }

    return { buttonClass: "btn btn-sm btn-warning", buttonText: "Follow" };
  };

  render() {
    const { loggedInUserFollowsUser, hover } = this.state;
    return (
      <>
        <div
          onClick={this.handleButtonClick}
          onKeyPress={this.handleButtonClick}
          onMouseEnter={this.toggleHover}
          onMouseLeave={this.toggleHover}
          className={this.getButtonDetails().buttonClass}
          style={{ marginLeft: "10px" }}
          role="button"
          tabIndex={0}
        >
          <i className="fas fa-plus" />
          <span>{this.getButtonDetails().buttonText}</span>
        </div>
        <br />
      </>
    );
  }
}

export default FollowButton;
