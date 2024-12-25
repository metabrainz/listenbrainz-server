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
import { act } from "react-dom/test-utils";
import { BrowserRouter } from "react-router-dom";
import FollowerFollowingModal from "../../../src/user/components/follow/FollowerFollowingModal";
import APIService from "../../../src/utils/APIService";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import UserListModalEntry from "../../../src/user/components/follow/UserListModalEntry";
import { ReactQueryWrapper } from "../../test-react-query";

const props = {
  user: { name: "foobar" },
  followerList: ["foo"],
  followingList: ["bar"],
  loggedInUserFollowsUser: () => true,
  updateFollowingList: () => {},
};

const globalContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  youtubeAuth: {},
  spotifyAuth: {},
  currentUser: {} as ListenBrainzUser,
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIService("foo"),
    { name: "Fnord" }
  ),
};

describe("<FollowerFollowingModal />", () => {
  it("renders", () => {
    const wrapper = mount(
      <GlobalAppContext.Provider value={globalContext}>
        <ReactQueryWrapper>
          <BrowserRouter>
            <FollowerFollowingModal {...props} />
          </BrowserRouter>
        </ReactQueryWrapper>
      </GlobalAppContext.Provider>
    );
    expect(wrapper.find(UserListModalEntry)).toHaveLength(1);
  });
  it("updates the mode correctly", async () => {
    const wrapper = mount(
      <GlobalAppContext.Provider value={globalContext}>
        <ReactQueryWrapper>
          <BrowserRouter>
            <FollowerFollowingModal {...props} />
          </BrowserRouter>
        </ReactQueryWrapper>
      </GlobalAppContext.Provider>
    );
    const instance = wrapper
      .find(FollowerFollowingModal)
      .instance() as FollowerFollowingModal;

    // initial state after first fetch
    expect(instance.state.activeMode).toEqual("following");

    // does nothing if the same mode as the current mode is passed
    await act(() => {
      instance.updateMode("following");
    });
    expect(instance.state.activeMode).toEqual("following");

    // updates the mode correctly
    await act(() => {
      instance.updateMode("follower");
    });
    expect(instance.state.activeMode).toEqual("follower");
  });
});
