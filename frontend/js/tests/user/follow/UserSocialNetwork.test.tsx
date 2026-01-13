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

  it("handles API errors gracefully with toast notifications", async () => {
    // Mock server to return error
    server.use(
      http.get("/1/user/*/followers", () => {
        return HttpResponse.json({ error: "Server error" }, { status: 500 });
      })
    );

    renderWithProviders(
      <QueryClientProvider client={queryClient}>
        <UserSocialNetwork {...props} />
      </QueryClientProvider>,
      globalContext
    );

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        expect.objectContaining({
          props: expect.objectContaining({
            title: "Error while fetching followers",
          }),
        }),
        { toastId: "fetch-followers-error" }
      );
    });
  });

  it("handles similar users API error gracefully", async () => {
  (toast.error as jest.Mock).mockClear();

 server.use(
  http.get("/1/user/:user/similar-users", () =>
    HttpResponse.json({ error: "Server error" }, { status: 500 })
  )
);

  renderWithProviders(
    <QueryClientProvider client={queryClient}>
      <UserSocialNetwork {...props} />
    </QueryClientProvider>,
    globalContext
  );

  await waitFor(() => {
    const calls = (toast.error as jest.Mock).mock.calls;

    const hasSimilarUsersError = calls.some(
      ([node, options]) =>
        node?.props?.title === " Error while fetching similar users" &&
        options?.toastId === "fetch-similar-error"
    );

    expect(hasSimilarUsersError).toBe(true);
  });
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




it("deduplicates 'user not found' errors using a shared toastId", async () => {
  (toast.error as jest.Mock).mockClear();

  server.use(
    http.get("/1/user/:user/followers", () =>
      HttpResponse.json({ error: "User not found" }, { status: 404 })
    ),
    http.get("/1/user/:user/following", () =>
      HttpResponse.json({ error: "User not found" }, { status: 404 })
    ),
    http.get("/1/user/:user/similar-users", () =>
      HttpResponse.json({ error: "User not found" }, { status: 404 })
    )
  );

renderWithProviders(
  <QueryClientProvider client={queryClient}>
    <UserSocialNetwork user={{ id: 2, name: "ghost" }} />
  </QueryClientProvider>,
  {
    ...globalContext,
    currentUser: { name: "loggedinuser" },
  }
);


  await waitFor(() => {
    const calls = (toast.error as jest.Mock).mock.calls;

    const userNotFoundCalls = calls.filter(
      ([node, options]) =>
        node?.props?.title === "User not found" &&
        options?.toastId === "user-not-found-error"
    );

    // We expect multiple calls, but all must share the same toastId
    expect(userNotFoundCalls.length).toBeGreaterThan(0);
    userNotFoundCalls.forEach(([, options]) => {
      expect(options.toastId).toBe("user-not-found-error");
    });
  });
});
});

