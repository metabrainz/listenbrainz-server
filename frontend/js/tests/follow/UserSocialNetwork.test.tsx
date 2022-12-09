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
import { mount, ReactWrapper } from "enzyme";

import { act } from "react-dom/test-utils";
import UserSocialNetwork, {
  UserSocialNetworkProps,
  UserSocialNetworkState,
} from "../../src/follow/UserSocialNetwork";
import FollowerFollowingModal from "../../src/follow/FollowerFollowingModal";
import SimilarUsersModal from "../../src/follow/SimilarUsersModal";

import * as userSocialNetworkProps from "../__mocks__/userSocialNetworkProps.json";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";

jest.useFakeTimers();

const { loggedInUser, ...otherProps } = userSocialNetworkProps;
const props = {
  ...otherProps,
  newAlert: jest.fn(),
};

const globalContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  youtubeAuth: {},
  spotifyAuth: {},
  currentUser: loggedInUser,
};

const similarUsers = [
  {
    similarity: 0.0839745792,
    user_name: "Cthulhu",
  },
  {
    similarity: 0.0779623581,
    user_name: "Dagon",
  },
];

const followingFollowers = ["bob", "fnord"];

describe("<UserSocialNetwork />", () => {
  let wrapper:
    | ReactWrapper<
        UserSocialNetworkProps,
        UserSocialNetworkState,
        UserSocialNetwork
      >
    | undefined;
  afterEach(() => {
    if (wrapper) {
      /* Unmount the wrapper at the end of each test, otherwise react-dom throws errors
        related to async lifecycle methods run against a missing dom 'document'.
        See https://github.com/facebook/react/issues/15691
      */
      wrapper.unmount();
    }
  });
  beforeEach(() => {
    wrapper = undefined;
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            // For similar users endpoint
            payload: similarUsers,
            following: followingFollowers,
            followers: followingFollowers,
          }),
      });
    });
  });

  it("renders correctly", () => {
    wrapper = mount(
      <GlobalAppContext.Provider value={globalContext}>
        <UserSocialNetwork {...props} />
      </GlobalAppContext.Provider>
    );
    expect(wrapper.html()).toMatchSnapshot();
  });

  it("contains a FollowerFollowingModal and a SimilarUsersModal components", () => {
    wrapper = mount(<UserSocialNetwork {...props} />);
    expect(wrapper).toBeTruthy();
    expect(wrapper.find(FollowerFollowingModal)).toHaveLength(1);
    expect(wrapper.find(SimilarUsersModal)).toHaveLength(1);
  });

  it("initializes by calling the API to get data", async () => {
    const consoleErrorSpy = jest.spyOn(console, "error");

    wrapper = mount<UserSocialNetwork>(
      <GlobalAppContext.Provider value={globalContext}>
        <UserSocialNetwork {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();

    await act(async () => {
      await instance.componentDidMount();
    });

    expect(consoleErrorSpy).not.toHaveBeenCalled();

    const similarUsersInState = [
      {
        name: "Cthulhu",
        similarityScore: 0.0839745792,
      },
      {
        name: "Dagon",
        similarityScore: 0.0779623581,
      },
    ];
    expect(instance.state.similarUsersList).toEqual(similarUsersInState);

    const expectedFollowingFollowersState = ["bob", "fnord"];
    expect(instance.state.followerList).toEqual(
      expectedFollowingFollowersState
    );
    expect(instance.state.followingList).toEqual(
      expectedFollowingFollowersState
    );
  });

  describe("updateFollowingList", () => {
    it("updates the state when called with action follow", async () => {
      wrapper = mount<UserSocialNetwork>(<UserSocialNetwork {...props} />);
      const instance = wrapper.instance();
      await act(async () => {
        await instance.componentDidMount();
      });

      // initial state after first fetch
      expect(instance.state.followingList).toEqual(["bob", "fnord"]);
      await act(async () => {
        instance.updateFollowingList({ name: "Baldur" }, "follow");
      });
      expect(instance.state.followingList).toEqual(["bob", "fnord", "Baldur"]);
    });

    it("updates the state when called with action unfollow", async () => {
      wrapper = mount<UserSocialNetwork>(<UserSocialNetwork {...props} />);
      const instance = wrapper.instance();
      await act(async () => {
        await instance.componentDidMount();
      });

      // initial state after first fetch
      expect(instance.state.followingList).toEqual(["bob", "fnord"]);
      await act(async () => {
        instance.updateFollowingList({ name: "fnord" }, "unfollow");
      });
      expect(instance.state.followingList).toEqual(["bob"]);
    });

    it("only allows adding a user once", async () => {
      wrapper = mount<UserSocialNetwork>(<UserSocialNetwork {...props} />);
      const instance = wrapper.instance();
      await act(async () => {
        await instance.componentDidMount();
      });
      await act(async () => {
        instance.updateFollowingList({ name: "Baldur" }, "follow");
      });
      expect(instance.state.followingList).toEqual(["bob", "fnord", "Baldur"]);

      // Ensure we can't add a user twice
      await act(async () => {
        instance.updateFollowingList({ name: "Baldur" }, "follow");
      });
      expect(instance.state.followingList).toEqual(["bob", "fnord", "Baldur"]);
    });

    it("does nothing when trying to unfollow a user that is not followed", async () => {
      wrapper = mount<UserSocialNetwork>(<UserSocialNetwork {...props} />);
      const instance = wrapper.instance();
      await act(async () => {
        await instance.componentDidMount();
      });

      expect(instance.state.followingList).toEqual(["bob", "fnord"]);
      await act(async () => {
        instance.updateFollowingList({ name: "Baldur" }, "unfollow");
      });
      expect(instance.state.followingList).toEqual(["bob", "fnord"]);
    });
  });

  describe("loggedInUserFollowsUser", () => {
    it("returns false if there is no logged in user", () => {
      // server sends an empty object in case no user is logged in
      wrapper = mount<UserSocialNetwork>(
        <GlobalAppContext.Provider
          value={{ ...globalContext, currentUser: {} as ListenBrainzUser }}
        >
          <UserSocialNetwork {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      expect(instance.loggedInUserFollowsUser({ name: "bob" })).toEqual(false);
    });

    it("returns false if user is not in followingList", async () => {
      wrapper = mount<UserSocialNetwork>(
        <GlobalAppContext.Provider value={globalContext}>
          <UserSocialNetwork {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      await act(async () => {
        await instance.componentDidMount();
      });

      expect(
        instance.loggedInUserFollowsUser({ name: "notarealuser" })
      ).toEqual(false);
    });

    it("returns true if user is in followingList", async () => {
      wrapper = mount<UserSocialNetwork>(
        <GlobalAppContext.Provider value={globalContext}>
          <UserSocialNetwork {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      await act(async () => {
        await instance.componentDidMount();
      });

      expect(instance.loggedInUserFollowsUser({ name: "fnord" })).toEqual(true);
    });
  });
});
