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
import { shallow } from "enzyme";
import UserPageHeading from "./UserPageHeading";
import FollowButton from "./FollowButton";

const user = {
  id: 1,
  name: "followed_user",
};

const loggedInUser = {
  id: 2,
  name: "iliekcomputers",
};

describe("<UserPageHeading />", () => {
  it("renders the name of the user", () => {
    const wrapper = shallow(
      <UserPageHeading
        user={user}
        loggedInUser={loggedInUser}
        loggedInUserFollowsUser
      />
    );
    expect(wrapper.contains("followed_user")).toBeTruthy();
  });

  it("does not render the FollowButton component if loggedInUser is null", () => {
    const wrapper = shallow(
      <UserPageHeading
        user={user}
        loggedInUser={null}
        loggedInUserFollowsUser={false}
      />
    );
    expect(wrapper.find(FollowButton)).toHaveLength(0);
  });

  it("does not render the FollowButton component if the loggedInUser is looking at their own page", () => {
    const wrapper = shallow(
      <UserPageHeading
        user={user}
        loggedInUser={user}
        loggedInUserFollowsUser={false}
      />
    );
    expect(wrapper.find(FollowButton)).toHaveLength(0);
  });

  it("renders the FollowButton component with the correct props if the loggedInUser and the user are different", () => {
    const wrapper = shallow(
      <UserPageHeading
        user={user}
        loggedInUser={loggedInUser}
        loggedInUserFollowsUser={false}
      />
    );
    const followButton = wrapper.find(FollowButton).at(0);
    expect(followButton.props()).toEqual({
      type: "icon-only",
      user: { id: 1, name: "followed_user" },
      loggedInUser: { id: 2, name: "iliekcomputers" },
      loggedInUserFollowsUser: false,
    });
  });
});
