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
import { shallow, mount, ReactWrapper } from "enzyme";
import FollowButton from "./FollowButton";

const user = {
  id: 1,
  name: "followed_user",
};

const loggedInUser = {
  id: 2,
  name: "iliekcomputers",
};

describe("<FollowButton />", () => {
  it("renders correct styling based on type prop", () => {
    // button is icon-only and renders text on hover
    let wrapper = mount(
      <FollowButton
        type="icon-only"
        user={user}
        loggedInUser={loggedInUser}
        loggedInUserFollowsUser
      />
    );
    expect(wrapper.html()).toMatchSnapshot();

    // button is solid and has no icon
    wrapper = mount(
      <FollowButton
        type="block"
        user={user}
        loggedInUser={loggedInUser}
        loggedInUserFollowsUser={false}
      />
    );
    expect(wrapper.html()).toMatchSnapshot();
  });

  it("renders with the correct text based on the props", () => {
    // already follows the user, should show "Following"
    let wrapper = shallow(
      <FollowButton
        type="icon-only"
        user={user}
        loggedInUser={loggedInUser}
        loggedInUserFollowsUser
      />
    );
    expect(wrapper.contains("Following")).toBeTruthy();

    // doesn't already follow the user, should show "Follow"
    wrapper = shallow(
      <FollowButton
        type="icon-only"
        user={user}
        loggedInUser={loggedInUser}
        loggedInUserFollowsUser={false}
      />
    );
    expect(wrapper.contains("Follow")).toBeTruthy();
    expect(wrapper.contains("Following")).toBeFalsy();

    // follows the user, hover, so should show "Unfollow"
    wrapper.setState({ loggedInUserFollowsUser: true, hover: true });
    wrapper.update();
    expect(wrapper.contains("Unfollow")).toBeTruthy();
  });

  describe("handleButtonClick", () => {
    const clickButton = (wrapper: ReactWrapper) => {
      wrapper.find(".follow-button").at(0).simulate("click");
    };

    const mockFollowAPICall = (instance: any, status: number) => {
      const spy = jest.spyOn(instance.context.APIService, "followUser");
      spy.mockImplementation(() => Promise.resolve({ status }));
      return spy;
    };

    const mockUnfollowAPICall = (instance: any, status: number) => {
      const spy = jest.spyOn(instance.context.APIService, "unfollowUser");
      spy.mockImplementation(() => Promise.resolve({ status }));
      return spy;
    };

    it("follows the user if logged in user isn't following the user", () => {
      const wrapper = mount(
        <FollowButton
          type="icon-only"
          user={user}
          loggedInUser={loggedInUser}
          loggedInUserFollowsUser={false}
        />
      );
      const instance = wrapper.instance();

      const spy = mockFollowAPICall(instance, 200);
      clickButton(wrapper);
      expect(spy).toHaveBeenCalledTimes(1);
    });

    it("unfollows the user if logged in user is already following the user", () => {
      const wrapper = mount(
        <FollowButton
          type="icon-only"
          user={user}
          loggedInUser={loggedInUser}
          loggedInUserFollowsUser
        />
      );
      const instance = wrapper.instance();

      const spy = mockUnfollowAPICall(instance, 200);
      clickButton(wrapper);
      expect(spy).toHaveBeenCalledTimes(1);
    });
  });
});
