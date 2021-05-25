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
import * as Sentry from "@sentry/react";
import FollowButton from "./FollowButton";
import APIService from "./APIService";
import GlobalAppContext, { GlobalAppContextT } from "./GlobalAppContext";

const UserPageHeading = ({
  user,
  loggedInUser,
  loggedInUserFollowsUser = false,
}: {
  user: ListenBrainzUser;
  loggedInUser: ListenBrainzUser | null;
  loggedInUserFollowsUser: boolean;
}) => {
  return (
    <h2 className="page-title">
      {user.name}
      {loggedInUser && user.name !== loggedInUser.name && (
        <FollowButton
          type="icon-only"
          user={user}
          loggedInUser={loggedInUser}
          loggedInUserFollowsUser={loggedInUserFollowsUser}
        />
      )}
    </h2>
  );
};

export default UserPageHeading;

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#user-page-heading-container");

  const propsElement = document.getElementById("react-props");
  const reactProps = JSON.parse(propsElement!.innerHTML);
  const {
    user,
    current_user,
    logged_in_user_follows_user,
    sentry_dsn,
    api_url,
  } = reactProps;

  const apiService: APIService = new APIService(
    api_url || `${window.location.origin}/1`
  );

  if (sentry_dsn) {
    Sentry.init({ dsn: sentry_dsn });
  }
  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
  };

  ReactDOM.render(
    <GlobalAppContext.Provider value={globalProps}>
      <UserPageHeading
        user={user}
        loggedInUser={current_user || null}
        loggedInUserFollowsUser={logged_in_user_follows_user}
      />
    </GlobalAppContext.Provider>,
    domContainer
  );
});
