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
import { BrowserRouter } from "react-router-dom";
import UserSocialNetwork, {
  UserSocialNetworkProps,
  UserSocialNetworkState,
} from "../../../src/user/components/follow/UserSocialNetwork";
import FollowerFollowingModal from "../../../src/user/components/follow/FollowerFollowingModal";
import SimilarUsersModal from "../../../src/user/components/follow/SimilarUsersModal";

import * as userSocialNetworkProps from "../../__mocks__/userSocialNetworkProps.json";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import { ReactQueryWrapper } from "../../test-react-query";

jest.useFakeTimers({ advanceTimers: true });

const { loggedInUser, ...otherProps } = userSocialNetworkProps;
const props = {
  ...otherProps,
};

const globalContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  youtubeAuth: {},
  spotifyAuth: {},
  currentUser: loggedInUser,
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIService("foo"),
    { name: "Fnord" }
  ),
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

const followingFollowers = ["jack", "fnord"];

describe("<UserSocialNetwork />", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });
  beforeAll(() => {
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

  it("contains a FollowerFollowingModal and a SimilarUsersModal components", () => {
    const wrapper = mount(
      <GlobalAppContext.Provider value={globalContext}>
        <ReactQueryWrapper>
          <BrowserRouter>
            <UserSocialNetwork {...props} />
          </BrowserRouter>
        </ReactQueryWrapper>
      </GlobalAppContext.Provider>
    );
    expect(wrapper.find(FollowerFollowingModal)).toHaveLength(1);
    expect(wrapper.find(SimilarUsersModal)).toHaveLength(1);
  });

  it("initializes by calling the API to get data", async () => {
    const consoleErrorSpy = jest.spyOn(console, "error");
    const wrapper = mount(
      <GlobalAppContext.Provider value={globalContext}>
        <ReactQueryWrapper>
          <BrowserRouter>
            <UserSocialNetwork {...props} />
          </BrowserRouter>
        </ReactQueryWrapper>
      </GlobalAppContext.Provider>
    );
    const instance = wrapper
      .find(UserSocialNetwork)
      .instance() as UserSocialNetwork;

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

    const expectedFollowingFollowersState = ["jack", "fnord"];
    expect(instance.state.followerList).toEqual(
      expectedFollowingFollowersState
    );
    expect(instance.state.followingList).toEqual(
      expectedFollowingFollowersState
    );
  });

  describe("updateFollowingList", () => {
    it("updates the state when called with action follow", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalContext}>
          <ReactQueryWrapper>
            <BrowserRouter>
              <UserSocialNetwork {...props} />
            </BrowserRouter>
          </ReactQueryWrapper>
        </GlobalAppContext.Provider>
      );
      const instance = wrapper
        .find(UserSocialNetwork)
        .instance() as UserSocialNetwork;
      await act(async () => {
        await instance.componentDidMount();
      });

      // initial state after first fetch
      expect(instance.state.currentUserFollowingList).toEqual(["jack", "fnord"]);
      await act(async () => {
        instance.updateFollowingList({ name: "Baldur" }, "follow");
      });
      expect(instance.state.currentUserFollowingList).toEqual(["jack", "fnord", "Baldur"]);
    });

    it("updates the state when called with action unfollow", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalContext}>
          <ReactQueryWrapper>
            <BrowserRouter>
              <UserSocialNetwork
                user={{
                  id: 1,
                  name: "iliekcomputers",
                }}
              />
            </BrowserRouter>
          </ReactQueryWrapper>
        </GlobalAppContext.Provider>
      );
      const instance = wrapper
        .find(UserSocialNetwork)
        .instance() as UserSocialNetwork;
      await act(async () => {
        await instance.componentDidMount();
      });

      // initial state after first fetch
      expect(instance.state.followingList).toEqual(["jack", "fnord"]);
      await act(async () => {
        instance.updateFollowingList({ name: "fnord" }, "unfollow");
      });
      expect(instance.state.followingList).toEqual(["jack"]);
    });

    it("does nothing, when called with action unfollow when it's not your own account", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalContext}>
          <ReactQueryWrapper>
            <BrowserRouter>
              <UserSocialNetwork {...props} />
            </BrowserRouter>
          </ReactQueryWrapper>
        </GlobalAppContext.Provider>
      );
      const instance = wrapper
        .find(UserSocialNetwork)
        .instance() as UserSocialNetwork;
      await act(async () => {
        await instance.componentDidMount();
      });

      // initial state after first fetch
      expect(instance.state.followingList).toEqual(["jack", "fnord"]);
      await act(async () => {
        instance.updateFollowingList({ name: "fnord" }, "unfollow");
      });

      // Since it's not your own account, it should not be removed from the following list
      expect(instance.state.followingList).toEqual(["jack", "fnord"]);
    });

    it("only allows adding a user once", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalContext}>
          <ReactQueryWrapper>
            <BrowserRouter>
              <UserSocialNetwork {...props} />
            </BrowserRouter>
          </ReactQueryWrapper>
        </GlobalAppContext.Provider>
      );
      const instance = wrapper
        .find(UserSocialNetwork)
        .instance() as UserSocialNetwork;
      await act(async () => {
        await instance.componentDidMount();
      });
      await act(async () => {
        instance.updateFollowingList({ name: "Baldur" }, "follow");
      });
      expect(instance.state.currentUserFollowingList).toEqual(["jack", "fnord", "Baldur"]);

      // Ensure we can't add a user twice
      await act(async () => {
        instance.updateFollowingList({ name: "Baldur" }, "follow");
      });
      expect(instance.state.currentUserFollowingList).toEqual(["jack", "fnord", "Baldur"]);
    });

    it("does nothing when trying to unfollow a user that is not followed", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalContext}>
          <ReactQueryWrapper>
            <BrowserRouter>
              <UserSocialNetwork {...props} />
            </BrowserRouter>
          </ReactQueryWrapper>
        </GlobalAppContext.Provider>
      );
      const instance = wrapper
        .find(UserSocialNetwork)
        .instance() as UserSocialNetwork;
      await act(async () => {
        await instance.componentDidMount();
      });

      expect(instance.state.followingList).toEqual(["jack", "fnord"]);
      await act(async () => {
        instance.updateFollowingList({ name: "Baldur" }, "unfollow");
      });
      expect(instance.state.followingList).toEqual(["jack", "fnord"]);
    });
  });

  describe("loggedInUserFollowsUser", () => {
    it("returns false if there is no logged in user", () => {
      // server sends an empty object in case no user is logged in
      const wrapper = mount(
        <GlobalAppContext.Provider
          value={{ ...globalContext, currentUser: {} as ListenBrainzUser }}
        >
          <ReactQueryWrapper>
            <BrowserRouter>
              <UserSocialNetwork {...props} />
            </BrowserRouter>
          </ReactQueryWrapper>
        </GlobalAppContext.Provider>
      );
      const instance = wrapper
        .find(UserSocialNetwork)
        .instance() as UserSocialNetwork;

      expect(instance.loggedInUserFollowsUser({ name: "bob" })).toEqual(false);
    });

    it("returns false if user is not in followingList", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalContext}>
          <ReactQueryWrapper>
            <BrowserRouter>
              <UserSocialNetwork {...props} />
            </BrowserRouter>
          </ReactQueryWrapper>
        </GlobalAppContext.Provider>
      );
      const instance = wrapper
        .find(UserSocialNetwork)
        .instance() as UserSocialNetwork;
      await act(async () => {
        await instance.componentDidMount();
      });

      expect(
        instance.loggedInUserFollowsUser({ name: "notarealuser" })
      ).toEqual(false);
    });

    it("returns true if user is in followingList", async () => {
      const wrapper = mount<UserSocialNetwork>(
        <GlobalAppContext.Provider value={globalContext}>
          <ReactQueryWrapper>
            <BrowserRouter>
              <UserSocialNetwork {...props} />
            </BrowserRouter>
          </ReactQueryWrapper>
        </GlobalAppContext.Provider>
      );
      const instance = wrapper
        .find(UserSocialNetwork)
        .instance() as UserSocialNetwork;
      await act(async () => {
        await instance.componentDidMount();
      });

      expect(instance.loggedInUserFollowsUser({ name: "fnord" })).toEqual(true);
    });
  });
});
