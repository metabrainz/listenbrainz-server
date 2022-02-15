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
import { mount } from "enzyme";
import FollowerFollowingModal from "../../src/follow/FollowerFollowingModal";
import APIService from "../../src/APIService";
import GlobalAppContext, { GlobalAppContextT } from "../../src/GlobalAppContext";

const props = {
  user: { name: "foobar" },
  followerList: ["foo"],
  followingList: ["bar"],
  loggedInUserFollowsUser: () => true,
  updateFollowingList: () => {},
};

const globalContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  youtubeAuth: {},
  spotifyAuth: {},
  currentUser: {} as ListenBrainzUser,
};

describe("<FollowerFollowingModal />", () => {
  it("renders", () => {
    const wrapper = mount<FollowerFollowingModal>(
      <GlobalAppContext.Provider value={globalContext}>
        <FollowerFollowingModal {...props} />
      </GlobalAppContext.Provider>
    );
    expect(wrapper.html()).toMatchSnapshot();
  });
});

describe("updateMode()", () => {
  it("updates the mode correctly", () => {
    const wrapper = mount<FollowerFollowingModal>(
      <GlobalAppContext.Provider value={globalContext}>
        <FollowerFollowingModal {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();

    // initial state after first fetch
    expect(instance.state.activeMode).toEqual("follower");

    // does nothing if the same mode as the current mode is passed
    instance.updateMode("follower");
    expect(instance.state.activeMode).toEqual("follower");

    // updates the mode correctly
    instance.updateMode("following");
    expect(instance.state.activeMode).toEqual("following");
  });
});
