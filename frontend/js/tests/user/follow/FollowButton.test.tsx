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
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FollowButton from "../../../src/user/components/follow/FollowButton";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";

const user = {
  id: 1,
  name: "followed_user",
};

const loggedInUser = {
  id: 2,
  name: "iliekcomputers",
  auth_token: "FNORD",
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

describe("<FollowButton />", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders correct styling based on type prop", () => {
    // button is icon-only and renders text on hover
    const { rerender } = render(
      <GlobalAppContext.Provider value={globalContext}>
        <FollowButton type="icon-only" user={user} loggedInUserFollowsUser />
      </GlobalAppContext.Provider>
    );

    let followButton = screen.getByRole("button");
    expect(followButton).toBeInTheDocument();
    expect(followButton).toHaveClass("lb-follow-button");
    expect(followButton).toHaveClass("following");
    expect(followButton).toHaveClass("icon-only");

    // button is solid and has no icon
    rerender(
      <GlobalAppContext.Provider value={globalContext}>
        <FollowButton
          type="block"
          user={user}
          loggedInUserFollowsUser={false}
        />
      </GlobalAppContext.Provider>
    );
    followButton = screen.getByRole("button");
    expect(followButton).toBeInTheDocument();
    expect(followButton).toHaveClass("lb-follow-button");
    expect(followButton).toHaveClass("block");
  });

  it("renders with the correct text based on the props and hover state", async () => {
    // already follows the user, should show "Following"
    const { rerender } = render(
      <GlobalAppContext.Provider value={globalContext}>
        <FollowButton type="icon-only" user={user} loggedInUserFollowsUser />
      </GlobalAppContext.Provider>
    );
    expect(screen.getByText("Following")).toBeInTheDocument();
    expect(screen.queryByText("Follow")).not.toBeInTheDocument();

    // doesn't already follow the user, should show "Follow"
    rerender(
      <GlobalAppContext.Provider value={globalContext}>
        <FollowButton
          type="icon-only"
          user={user}
          loggedInUserFollowsUser={false}
        />
      </GlobalAppContext.Provider>
    );
    expect(screen.getByText("Follow")).toBeInTheDocument();
    expect(screen.queryByText("Following")).not.toBeInTheDocument();

    // follows the user, hover, so should show "Unfollow"
    // Rerender with loggedInUserFollowsUser as true to set up the "following" state
    rerender(
      <GlobalAppContext.Provider value={globalContext}>
        <FollowButton type="icon-only" user={user} loggedInUserFollowsUser />
      </GlobalAppContext.Provider>
    );
    const followButton = screen.getByRole("button");
    expect(followButton).toHaveTextContent("Following"); // Initially "Following"

    await userEvent.hover(followButton);
    // After hover, it should change to "Unfollow" if loggedInUserFollowsUser is true
    expect(screen.queryByText("Following")).not.toBeInTheDocument();
    expect(followButton).toHaveTextContent("Unfollow");
  });

  describe("handleButtonClick", () => {
    const mockFollowAPICall = (status: number) => {
      const spy = jest.spyOn(globalContext.APIService, "followUser");
      spy.mockImplementation(() => Promise.resolve({ status }));
      return spy;
    };

    const mockUnfollowAPICall = (status: number) => {
      const spy = jest.spyOn(globalContext.APIService, "unfollowUser");
      spy.mockImplementation(() => Promise.resolve({ status }));
      return spy;
    };

    it("follows the user if logged in user isn't following the user", async () => {
      render(
        <GlobalAppContext.Provider value={globalContext}>
          <FollowButton
            type="icon-only"
            user={user}
            loggedInUserFollowsUser={false}
          />
        </GlobalAppContext.Provider>
      );
      const followButton = screen.getByRole("button", { name: "Follow" });

      const spy = mockFollowAPICall(200);
      await userEvent.click(followButton);

      await waitFor(() => {
        expect(spy).toHaveBeenCalledTimes(1);
        expect(spy).toHaveBeenCalledWith("followed_user", "FNORD");
      });
      // Verify button text changes to "Following" after successful follow
      expect(
        screen.getByRole("button", { name: "Following" })
      ).toBeInTheDocument();
    });

    it("unfollows the user if logged in user is already following the user", async () => {
      render(
        <GlobalAppContext.Provider value={globalContext}>
          <FollowButton type="icon-only" user={user} loggedInUserFollowsUser />
        </GlobalAppContext.Provider>
      );
      const followButton = screen.getByRole("button", { name: "Following" });
      expect(followButton).toBeInTheDocument();

      // Hover to reveal "Unfollow" text
      await userEvent.hover(followButton);
      const unfollowButton = screen.getByRole("button", { name: "Unfollow" });

      const spy = mockUnfollowAPICall(200);
      await userEvent.click(unfollowButton);

      await waitFor(() => {
        expect(spy).toHaveBeenCalledTimes(1);
        expect(spy).toHaveBeenCalledWith("followed_user", "FNORD");
      });
      // Verify button text changes back to "Follow" after successful unfollow
      expect(
        screen.getByRole("button", { name: "Follow" })
      ).toBeInTheDocument();
    });

    it("shows error state if follow fails", async () => {
      render(
        <GlobalAppContext.Provider value={globalContext}>
          <FollowButton
            type="icon-only"
            user={user}
            loggedInUserFollowsUser={false}
          />
        </GlobalAppContext.Provider>
      );
      const followButton = screen.getByRole("button", { name: "Follow" });

      const spy = mockFollowAPICall(500); // Simulate an error
      await userEvent.click(followButton);

      await waitFor(() => {
        expect(spy).toHaveBeenCalledTimes(1);
      });
      expect(
        screen.getByRole("button", { name: "Error!!" })
      ).toBeInTheDocument();
    });

    it("shows error state if unfollow fails", async () => {
      render(
        <GlobalAppContext.Provider value={globalContext}>
          <FollowButton type="icon-only" user={user} loggedInUserFollowsUser />
        </GlobalAppContext.Provider>
      );
      const followButton = screen.getByRole("button", { name: "Following" });
      await userEvent.hover(followButton); // Hover to get "Unfollow" text
      const unfollowButton = screen.getByRole("button", { name: "Unfollow" });

      const spy = mockUnfollowAPICall(500); // Simulate an error
      await userEvent.click(unfollowButton);

      await waitFor(() => {
        expect(spy).toHaveBeenCalledTimes(1);
      });
      expect(
        screen.getByRole("button", { name: "Error!!" })
      ).toBeInTheDocument();
    });
  });

  it("updates state when loggedInUserFollowsUser prop changes", async () => {
    const { rerender } = render(
      <GlobalAppContext.Provider value={globalContext}>
        <FollowButton
          type="icon-only"
          user={user}
          loggedInUserFollowsUser={false}
        />
      </GlobalAppContext.Provider>
    );

    expect(screen.getByText("Follow")).toBeInTheDocument();

    // Simulate prop change
    rerender(
      <GlobalAppContext.Provider value={globalContext}>
        <FollowButton
          type="icon-only"
          user={user}
          loggedInUserFollowsUser={true}
        />
      </GlobalAppContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText("Following")).toBeInTheDocument();
    });

    // Simulate prop change back
    rerender(
      <GlobalAppContext.Provider value={globalContext}>
        <FollowButton
          type="icon-only"
          user={user}
          loggedInUserFollowsUser={false}
        />
      </GlobalAppContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText("Follow")).toBeInTheDocument();
    });
  });
});
