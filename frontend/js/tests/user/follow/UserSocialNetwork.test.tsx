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
import { screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import { toast } from "react-toastify";

import UserSocialNetwork from "../../../src/user/components/follow/UserSocialNetwork";
import { GlobalAppContextT } from "../../../src/utils/GlobalAppContext";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

import * as userSocialNetworkProps from "../../__mocks__/userSocialNetworkProps.json";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock react-toastify
jest.mock("react-toastify", () => ({
  toast: {
    error: jest.fn(),
  },
}));

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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

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

const mockArtists = [
  {
    artist_name: "Artist1",
    artist_mbid: "mbid1",
    listen_count: 100,
  },
  {
    artist_name: "Artist2",
    artist_mbid: "mbid2",
    listen_count: 50,
  },
];

describe("<UserSocialNetwork />", () => {
  let server: SetupServerApi;

  beforeAll(() => {
    const handlers = [
      http.get("/1/user/*/followers", () => {
        return HttpResponse.json({
          followers: followingFollowers,
        });
      }),
      http.get("/1/user/*/following", () => {
        return HttpResponse.json({
          following: followingFollowers,
        });
      }),
      http.get("/1/user/*/similar", () => {
        return HttpResponse.json({
          payload: similarUsers,
        });
      }),
      http.get("/1/user/*/similar-to/*", () => {
        return HttpResponse.json({
          payload: { similarity: 0.5 },
        });
      }),
      http.get("/1/user/*/artists", () => {
        return HttpResponse.json({
          payload: { artists: mockArtists },
        });
      }),
    ];
    server = setupServer(...handlers);
    server.listen();
  });

  afterEach(() => {
    server.resetHandlers();
    jest.clearAllMocks();
  });

  afterAll(() => {
    server.close();
  });

  it("renders FollowerFollowingCards and SimilarUsersModal components", async () => {
    renderWithProviders(<UserSocialNetwork {...props} />, globalContext);

    await waitFor(() => {
      expect(
        screen.getByTestId("follower-following-cards")
      ).toBeInTheDocument();
      expect(screen.getByTestId("similar-users-modal")).toBeInTheDocument();
    });
  });

  it("renders CompatibilityCard when viewing another user's profile", async () => {
    const differentUserProps = {
      user: { id: 2, name: "differentuser" },
    };

    renderWithProviders(
      <UserSocialNetwork {...differentUserProps} />,
      globalContext
    );

    await waitFor(() => {
      expect(screen.getByTestId("compatibility-card")).toBeInTheDocument();
    });
  });

  it("does not render CompatibilityCard when viewing own profile", async () => {
    const ownProfileProps = {
      user: { id: 1, name: loggedInUser.name },
    };

    renderWithProviders(
      <UserSocialNetwork {...ownProfileProps} />,
      globalContext
    );

    await waitFor(() => {
      expect(
        screen.queryByTestId("compatibility-card")
      ).not.toBeInTheDocument();
    });
  });

  it("fetches and displays follower and following data on mount", async () => {
    // Spy on the API calls to verify they're made with correct parameters
    const getFollowersOfUserSpy = jest.spyOn(
      globalContext.APIService,
      "getFollowersOfUser"
    );
    const getFollowingForUserSpy = jest.spyOn(
      globalContext.APIService,
      "getFollowingForUser"
    );

    // Mock the API responses
    getFollowersOfUserSpy.mockResolvedValue({ followers: followingFollowers });
    getFollowingForUserSpy.mockResolvedValue({ following: followingFollowers });

    renderWithProviders(
      <QueryClientProvider client={queryClient}>
        <UserSocialNetwork {...props} />
      </QueryClientProvider>,
      globalContext
    );

    // Wait for component to mount and make API calls
    await waitFor(() => {
      expect(getFollowersOfUserSpy).toHaveBeenCalledWith(props.user.name);
      expect(getFollowingForUserSpy).toHaveBeenCalledWith(props.user.name);
    });

    // Verify the modal component receives the data (check if it's rendered)
    await waitFor(() => {
      const followerModal = screen.getByTestId("follower-following-cards");
      expect(followerModal).toBeInTheDocument();

      expect(followerModal).toHaveTextContent("jack");
      expect(followerModal).toHaveTextContent("fnord");
    });

    // Clean up
    getFollowersOfUserSpy.mockRestore();
    getFollowingForUserSpy.mockRestore();
  });

  it("fetches and displays similar users data on mount", async () => {
    // Spy on the API call
    const getSimilarUsersForUserSpy = jest.spyOn(
      globalContext.APIService,
      "getSimilarUsersForUser"
    );
    getSimilarUsersForUserSpy.mockResolvedValue({ payload: similarUsers });

    renderWithProviders(
      <QueryClientProvider client={queryClient}>
        <UserSocialNetwork {...props} />
      </QueryClientProvider>,
      globalContext
    );

    // Wait for API call to be made
    await waitFor(() => {
      expect(getSimilarUsersForUserSpy).toHaveBeenCalledWith(props.user.name);
    });

    // Verify the similar users modal is rendered
    await waitFor(() => {
      const similarUsersModal = screen.getByTestId("similar-users-modal");
      expect(similarUsersModal).toBeInTheDocument();

      expect(similarUsersModal).toHaveTextContent("Cthulhu");
      expect(similarUsersModal).toHaveTextContent("Dagon");
    });

    // Clean up
    getSimilarUsersForUserSpy.mockRestore();
  });

 it("handles similar users API error gracefully", async () => {
  (toast.error as jest.Mock).mockClear();

  const spy = jest
    .spyOn(globalContext.APIService, "getSimilarUsersForUser")
    .mockRejectedValue(new Error("Server error"));

  renderWithProviders(
    <UserSocialNetwork {...props} />,
    globalContext
  );

  await waitFor(() => {
    const calls = (toast.error as jest.Mock).mock.calls;

    const hasSimilarUsersError = calls.some(
      ([node, options]) =>
        node?.props?.title === "Error while fetching similar users" &&
        options?.toastId === "fetch-similar-error"
    );

    expect(hasSimilarUsersError).toBe(true);
  });

  spy.mockRestore();
});




  it("does not fetch similarity data when not logged in", async () => {
    const contextWithoutUser = {
      ...globalContext,
      currentUser: undefined,
    };

    renderWithProviders(
      <QueryClientProvider client={queryClient}>
        <UserSocialNetwork {...props} />
      </QueryClientProvider>,
      contextWithoutUser
    );

    await waitFor(() => {
      expect(
        screen.queryByTestId("compatibility-card")
      ).not.toBeInTheDocument();
    });
  });

  it("does not fetch similarity data when viewing own profile", async () => {
    const ownProfileProps = {
      user: { id: 1, name: loggedInUser.name },
    };

    renderWithProviders(
      <QueryClientProvider client={queryClient}>
        <UserSocialNetwork {...ownProfileProps} />
      </QueryClientProvider>,
      globalContext
    );

    await waitFor(() => {
      expect(
        screen.queryByTestId("compatibility-card")
      ).not.toBeInTheDocument();
    });
  });

  it("silently handles 'Similar-to user not found' error", async () => {
    server.use(
      http.get("/1/user/*/similar-to/*", () => {
        return HttpResponse.json(
          { error: "Similar-to user not found" },
          { status: 404 }
        );
      })
    );

    const differentUserProps = {
      user: { id: 2, name: "differentuser" },
    };

    renderWithProviders(
      <QueryClientProvider client={queryClient}>
        <UserSocialNetwork {...differentUserProps} />
      </QueryClientProvider>,
      globalContext
    );

    await waitFor(() => {
      // Should not show error toast for this specific error
      expect(toast.error).not.toHaveBeenCalledWith(
        expect.objectContaining({
          props: expect.objectContaining({
            title: "Error while fetching similarity",
          }),
        }),
        { toastId: "fetch-similarity-error" }
      );
    });
  });

  it("re-fetches data when profileUser changes", async () => {
    const { rerender } = renderWithProviders(
      <QueryClientProvider client={queryClient}>
        <UserSocialNetwork user={{ id: 1, name: "user1" }} />
      </QueryClientProvider>,
      globalContext
    );

    await waitFor(() => {
      expect(
        screen.getByTestId("follower-following-cards")
      ).toBeInTheDocument();
    });

    // Change the user prop
    rerender(
      <QueryClientProvider client={queryClient}>
        <UserSocialNetwork user={{ id: 2, name: "user2" }} />
      </QueryClientProvider>
    );

    // Should trigger new API calls and re-render
    await waitFor(() => {
      expect(
        screen.getByTestId("follower-following-cards")
      ).toBeInTheDocument();
    });
  });

describe("User not found error deduplication", () => {
  it("should use the same toastId for all user-not-found errors to prevent duplicates", async () => {
    // Spy on toast.error to track calls
    const toastErrorSpy = jest.spyOn(toast, "error");

    // Set up MSW handlers to return 404 for all user-related endpoints
    server.use(
      http.get("*/user/nonexistent_user/followers", () => {
        return HttpResponse.json(
          { code: 404, error: "User not found" },
          { status: 404 }
        );
      }),
      http.get("*/user/nonexistent_user/following", () => {
        return HttpResponse.json(
          { code: 404, error: "User not found" },
          { status: 404 }
        );
      }),
      http.get("*/user/nonexistent_user/similar-users", () => {
        return HttpResponse.json(
          { code: 404, error: "User not found" },
          { status: 404 }
        );
      })
    );

    // Render the component with a non-existent user
    renderWithProviders(
      <UserSocialNetwork user={{ name: "nonexistent_user" }} />,
      globalContext
    );

    // Wait for API calls to complete and toasts to be triggered
    await waitFor(
      () => {
        expect(toastErrorSpy).toHaveBeenCalled();
      },
      { timeout: 3000 }
    );

    // Filter toast.error calls that are for "User not found" errors
    const userNotFoundCalls = toastErrorSpy.mock.calls.filter((call) => {
      const message = call[0]; // First argument is the message/component
      const options = call[1];  // Second argument contains the options
      
      // Check if this is a user-not-found error by looking at the message title
      return (
        typeof message === "object" &&
        message !== null &&
        "props" in message &&
        message.props &&
        message.props.title === "User not found"
      );
    });

    // We expect multiple API calls to fail (followers, following, similar-users)
    // so toast.error should be called multiple times
    expect(userNotFoundCalls.length).toBeGreaterThan(1);

    // The key assertion: ALL user-not-found errors should use the SAME toastId
    // This is what prevents duplicate toasts from appearing to the user
    const toastIds = userNotFoundCalls.map(call => {
      const options = call[1];
      return options && typeof options === "object" ? options.toastId : undefined;
    });
    const uniqueToastIds = new Set(toastIds);
    
    // All should have the same toastId
    expect(uniqueToastIds.size).toBe(1);
    expect(uniqueToastIds.has("user-not-found-error")).toBe(true);
    
    // Verify that each call actually has the toastId set
    toastIds.forEach(toastId => {
      expect(toastId).toBe("user-not-found-error");
    });

    // Clean up
    toastErrorSpy.mockRestore();
  });
});

});

