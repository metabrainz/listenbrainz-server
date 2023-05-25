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
import { mount, ReactWrapper, shallow } from "enzyme";
import UserPageHeading from "../../src/user/UserPageHeading";
import FollowButton from "../../src/follow/FollowButton";
import ReportUserButton from "../../src/report-user/ReportUser";
import ReportUserModal from "../../src/report-user/ReportUserModal";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";
import { waitForComponentToPaint } from "../test-utils";

const user = {
  id: 1,
  name: "followed_user",
};

const loggedInUser = {
  id: 2,
  name: "iliekcomputers",
};

// Create a new instance of GlobalAppContext
const globalContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  youtubeAuth: {},
  spotifyAuth: {},
  currentUser: loggedInUser,
};

describe("UserPageHeading", () => {
  it("renders the name of the user", () => {
    const shallowWrapper = shallow(
      <UserPageHeading
        user={user}
        loggedInUser={loggedInUser}
        loggedInUserFollowsUser
        alreadyReportedUser={false}
      />
    );
    expect(shallowWrapper.contains("followed_user")).toBeTruthy();
  });

  it("does not render the FollowButton component if no loggedInUser", () => {
    // server sends an empty object in case no user is logged in
    const shallowWrapper = shallow(
      <UserPageHeading
        user={user}
        loggedInUser={{} as ListenBrainzUser}
        loggedInUserFollowsUser={false}
        alreadyReportedUser={false}
      />
    );
    expect(shallowWrapper.find(FollowButton)).toHaveLength(0);
  });

  it("does not render the FollowButton component if the loggedInUser is looking at their own page", () => {
    const shallowWrapper = shallow(
      <UserPageHeading
        user={user}
        loggedInUser={user}
        loggedInUserFollowsUser={false}
        alreadyReportedUser={false}
      />
    );
    expect(shallowWrapper.find(FollowButton)).toHaveLength(0);
  });

  it("renders the FollowButton component with the correct props if the loggedInUser and the user are different", () => {
    const shallowWrapper = shallow(
      <UserPageHeading
        user={user}
        loggedInUser={loggedInUser}
        loggedInUserFollowsUser={false}
        alreadyReportedUser={false}
      />
    );
    const followButton = shallowWrapper.find(FollowButton).at(0);
    expect(followButton.props()).toEqual({
      type: "icon-only",
      user: { id: 1, name: "followed_user" },
      loggedInUserFollowsUser: false,
    });
  });

  describe("ReportUser", () => {
    it("does not render a ReportUserButton nor ReportUserModal components if user is not logged in", () => {
      // server sends an empty object in case no user is logged in
      const shallowWrapper = shallow(
        <UserPageHeading
          user={user}
          loggedInUser={{} as ListenBrainzUser}
          loggedInUserFollowsUser={false}
          alreadyReportedUser={false}
        />
      );

      expect(shallowWrapper.find(ReportUserButton)).toHaveLength(0);
      expect(shallowWrapper.find(ReportUserModal)).toHaveLength(0);
    });

    it("renders the ReportUserButton and ReportUserModal components with the correct props inside the UserPageHeading", () => {
      const wrapper = mount(
        <UserPageHeading
          user={user}
          loggedInUser={loggedInUser}
          loggedInUserFollowsUser={false}
          alreadyReportedUser={false}
        />
      );

      const reportUserButton = wrapper.find(ReportUserButton).first();
      expect(reportUserButton.props()).toEqual({
        user: { id: 1, name: "followed_user" },
        alreadyReported: false,
      });
      const reportUserModal = wrapper.find(ReportUserModal).first();

      expect(reportUserModal).toBeDefined();
      const reportUserModalProps = reportUserModal.props();
      expect(reportUserModalProps.reportedUserName).toEqual("followed_user");
    });

    it("allows to report a user using the ReportUserModal", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalContext}>
          <ReportUserButton user={user} alreadyReported={false} />
        </GlobalAppContext.Provider>
      );
      const reportUserButton = wrapper.instance();
      const reportUserModal = wrapper.find(ReportUserModal).first();

      //  Check initial state
      expect(wrapper.state("reported")).toBeFalsy();
      const reportUserButtonHTMLElement = wrapper.find("button").first();
      expect(reportUserButtonHTMLElement.text()).toEqual("Report User");

      const apiCallSpy = jest.fn().mockImplementation(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: "followed_user has been reported successfully.",
            }),
        })
      );
      (reportUserButton.context as GlobalAppContextT).APIService.reportUser = apiCallSpy;

      // Let's pretend we're writing in the textarea
      const reasonInput = reportUserModal.find("#reason").first();
      expect(reasonInput).toBeDefined();
      reasonInput.simulate("change", {
        target: { value: "Can you see the Fnords?" },
      });
      // And then we click on the submit button
      const submitButton = reportUserModal
        .find("button[type='submit']")
        .first();
      submitButton.simulate("click");

      await waitForComponentToPaint(wrapper);

      expect(apiCallSpy).toHaveBeenCalledWith(
        "followed_user",
        "Can you see the Fnords?"
      );

      expect(wrapper.state("reported")).toBeTruthy();
      expect(reportUserButtonHTMLElement.text()).toEqual("Report Submitted");
    });

    it("displays a user firendly message in the button text in case of error", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalContext}>
          <ReportUserButton user={user} alreadyReported={false} />
        </GlobalAppContext.Provider>
      );
      const reportUserButton = wrapper.instance();
      const reportUserModal = wrapper.find(ReportUserModal).first();

      expect(wrapper.state("reported")).toBeFalsy();
      const reportUserButtonHTMLElement = wrapper.find("button").first();
      expect(reportUserButtonHTMLElement.text()).toEqual("Report User");

      const apiCallSpy = jest
        .fn()
        .mockImplementation(() =>
          Promise.reject(new Error("You cannot report yourself"))
        );
      (reportUserButton.context as GlobalAppContextT).APIService.reportUser = apiCallSpy;

      const submitButton = reportUserModal
        .find("button[type='submit']")
        .first();
      submitButton.simulate("click");

      await waitForComponentToPaint(wrapper);

      expect(apiCallSpy).toHaveBeenCalledWith("followed_user", "");
      expect(wrapper.state("reported")).toBeFalsy();
      expect(reportUserButtonHTMLElement.text()).toEqual("Error! Try Again");
    });
  });
});
