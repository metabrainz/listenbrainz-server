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
import * as ReactDOM from "react-dom";
import FollowButton from "./FollowButton";

// Using this function to limit access to the follow button
// while it does nothing. Will eventually remove this function.
// TODO (param, 2020-09-30): remove this function
const followUsersFeatureEnabled = (currentUser: string): boolean => {
  const usersAllowedIn = [
    "rob",
    "iliekcomputers",
    "shivam-kapila",
    "ishaanshah",
    "Mr_Monkey",
  ];
  return usersAllowedIn.includes(currentUser);
};

const UserPageHeading = ({
  user,
  loggedInUser,
  loggedInUserFollowsUser,
}: {
  user: ListenBrainzUser;
  loggedInUser: ListenBrainzUser;
  loggedInUserFollowsUser: boolean;
}) => {
  return (
    <>
      <h2 className="page-title">
        {user.name}
        {loggedInUser &&
          followUsersFeatureEnabled(loggedInUser.name) &&
          user.name !== loggedInUser.name && (
            <FollowButton
              user={user}
              loggedInUser={loggedInUser}
              loggedInUserFollowsUser={loggedInUserFollowsUser}
            />
          )}
      </h2>
    </>
  );
};

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#follow-controls-container");

  const propsElement = document.getElementById("react-props");
  const reactProps = JSON.parse(propsElement!.innerHTML);
  const { user, current_user, logged_in_user_follows_user } = reactProps;
  ReactDOM.render(
    <UserPageHeading
      user={user}
      loggedInUser={current_user || null}
      loggedInUserFollowsUser={logged_in_user_follows_user}
    />,
    domContainer
  );
});
