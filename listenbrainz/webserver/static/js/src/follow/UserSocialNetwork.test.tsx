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
import { mount, shallow } from "enzyme";

import UserSocialNetwork from "./UserSocialNetwork";
import FollowerFollowingModal from "./FollowerFollowingModal";
import SimilarUsersModal from "./SimilarUsersModal";

import * as props from "./__mocks__/userSocialNetworkProps.json";

describe("<UserSocialNetwork />", () => {
  beforeAll(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            // For similar users endpoint
            payload: [
              {
                similarity: 0.0839745792,
                user_name: "Cthulhu",
              },
              {
                similarity: 0.0779623581,
                user_name: "Dagon",
              },
            ],
            // For following/followers endpoint
            following: [],
            followers: [],
          }),
      });
    });
  });

  it("renders correctly", () => {
    const wrapper = shallow(<UserSocialNetwork {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
  });

  it("contains a FollowerFollowingModal and a SimilarUsersModal components", () => {
    const wrapper = shallow(<UserSocialNetwork {...props} />);
    expect(wrapper).toBeTruthy();
    expect(wrapper.find(FollowerFollowingModal)).toHaveLength(1);
    expect(wrapper.find(SimilarUsersModal)).toHaveLength(1);
  });

  it("calls getSimilarUsers with the right user name", () => {
    const wrapper = shallow<UserSocialNetwork>(
      <UserSocialNetwork {...props} />
    );
    const instance = wrapper.instance();

    const spy = jest.fn().mockImplementation(() => Promise.resolve({}));
    // eslint-disable-next-line dot-notation
    instance["APIService"].getSimilarUsersForUser = spy;

    expect(spy).toHaveBeenCalledWith("bob");
  });

  it("calls getFollowers with the right user name", () => {
    const wrapper = shallow<UserSocialNetwork>(
      <UserSocialNetwork {...props} />
    );
    const instance = wrapper.instance();

    const spy = jest.fn().mockImplementation(() => Promise.resolve({}));
    // eslint-disable-next-line dot-notation
    instance["APIService"].getFollowersOfUser = spy;

    expect(spy).toHaveBeenCalledWith("iliekcomputers");
  });
  it("calls getFollowing with the right user name", () => {
    const wrapper = shallow<UserSocialNetwork>(
      <UserSocialNetwork {...props} />
    );
    const instance = wrapper.instance();

    const spy = jest.fn().mockImplementation(() => Promise.resolve({}));
    // eslint-disable-next-line dot-notation
    instance["APIService"].getFollowingForUser = spy;

    expect(spy).toHaveBeenCalledWith("bob");
  });
});
