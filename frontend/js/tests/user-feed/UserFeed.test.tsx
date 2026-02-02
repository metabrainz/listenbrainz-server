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

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import userEvent from "@testing-library/user-event";
import UserFeedPage from "../../src/user-feed/UserFeed";
import { EventType } from "../../src/user-feed/types";
import * as timelineProps from "../__mocks__/timelineProps.json";

import {
  renderWithProviders,
  textContentMatcher,
} from "../test-utils/rtl-test-utils";
import GlobalAppContext, {
  defaultGlobalContext,
} from "../../src/utils/GlobalAppContext";

jest.unmock("react-toastify");

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});
const queryKey = ["feed", {}];

const reactQueryWrapper = ({ children }: any) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe("UserFeed", () => {
  let server: SetupServerApi;
  beforeAll(async () => {
    // Mock the server responses
    const handlers = [
      http.get("http://localhost/1/user/*/feed/events", async (path) => {
        // return feed events
        return HttpResponse.json({ payload: timelineProps });
      }),
      http.get("http://localhost/1/user/*/following", () =>
        HttpResponse.json({ following: [] })
      ),
      http.get("http://localhost/1/user/*/followers", () =>
        HttpResponse.json({ followers: [] })
      ),
      http.get("http://localhost/1/user/*/similar-users", () =>
        HttpResponse.json({ payload: [] })
      ),
    ];
    server = setupServer(...handlers);
    server.listen();
  });
  afterEach(() => {
    queryClient.cancelQueries();
    queryClient.clear();
  });
  afterAll(() => {
    server.close();
  });

  it("renders correctly", async () => {
    renderWithProviders(
      <UserFeedPage />,
      {
        currentUser: {
          id: 1,
          name: "FNORD",
          auth_token: "never_gonna",
        },
      },
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      const state = queryClient.getQueryState(queryKey);
      expect(state?.status === "success").toBeTruthy();
    });

    const timeline = screen.getByTestId("timeline");
    expect(timeline).toBeInTheDocument();
    expect(within(timeline).getAllByRole("listitem")).toHaveLength(
      timelineProps.events.length
    );

    expect(screen.getByText("Latest activity")).toBeInTheDocument();
  });

  it("has infinite pagination", async () => {
    renderWithProviders(
      <UserFeedPage />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      expect(queryClient.getQueryState(queryKey)?.data).toBeDefined();
    });

    const timeline = screen.getByTestId("timeline");
    expect(timeline).toBeInTheDocument();
    expect(within(timeline).getAllByRole("listitem")).toHaveLength(
      timelineProps.events.length
    );

    const loadMoreButton = screen.getByText("Load More");
    const rightNow = Date.now();
    await userEvent.click(loadMoreButton);
    expect(
      queryClient.getQueryState(queryKey)?.dataUpdatedAt
    ).toBeGreaterThanOrEqual(rightNow);
  });

  it("renders recording recommendation events", async () => {
    queryClient.cancelQueries();
    queryClient.setQueryData(queryKey, {
      pages: [
        {
          events: timelineProps.events.filter(
            (event) => event.event_type === EventType.RECORDING_RECOMMENDATION
          ),
        },
      ],
      pageParams: [Date.now()],
    });

    renderWithProviders(
      <UserFeedPage />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      expect(queryClient.getQueryState(queryKey)?.status).toEqual("success");
    });
    const timeline = screen.getByTestId("timeline");
    expect(timeline).toBeInTheDocument();
    expect(within(timeline).getAllByRole("listitem")).toHaveLength(7);
    expect(
      screen.getAllByText(textContentMatcher("reosarevok recommended a track"))
    ).toHaveLength(7);
    screen.getByText("Kust on tulnud muodike");
    screen.getByText("Mar 02, 2021, 7:48 PM");
  });

  it("renders follow relationship events", async () => {
    queryClient.setQueryData(queryKey, {
      pages: [
        {
          events: timelineProps.events.filter(
            (event) => event.event_type === EventType.FOLLOW
          ),
        },
      ],
      pageParams: [Date.now()],
    });
    renderWithProviders(
      // Not sure why we have to pass a context here, as one is alreqady added when we
      // call renderWithProviders, but without it currentUser is not set as expected
      <GlobalAppContext.Provider
        value={{
          ...defaultGlobalContext,
          currentUser: timelineProps.currentUser,
        }}
      >
        <UserFeedPage />
      </GlobalAppContext.Provider>,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      expect(queryClient.getQueryState(queryKey)?.status).toEqual("success");
    });
    screen.getByText(textContentMatcher("You are now following reosarevok"));
    screen.getByText("Feb 16, 2021, 11:21 AM");
    screen.getByText(textContentMatcher("reosarevok is now following you"));
    screen.getByText("Feb 16, 2021, 11:20 AM");
    const timeline = screen.getByTestId("timeline");
    expect(timeline).toBeInTheDocument();
    expect(within(timeline).getAllByRole("listitem")).toHaveLength(2);
  });

  it("renders notification events", async () => {
    queryClient.setQueryData(queryKey, {
      pages: [
        {
          events: timelineProps.events.filter(
            (event) => event.event_type === EventType.NOTIFICATION
          ),
        },
      ],
      pageParams: [Date.now()],
    });

    renderWithProviders(
      <UserFeedPage />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      expect(queryClient.getQueryState(queryKey)?.status).toEqual("success");
    });
    const timeline = screen.getByTestId("timeline");
    expect(timeline).toBeInTheDocument();
    expect(within(timeline).getAllByRole("listitem")).toHaveLength(1);
    screen.getByText(
      textContentMatcher(
        "We have created a playlist for you: My top discoveries of 2020"
      )
    );
    screen.getByText("Feb 16, 2021, 11:17 AM");
    expect(within(timeline).getByRole("link")).toHaveAttribute(
      "href",
      "https://listenbrainz.org/playlist/4245ccd3-4f0d-4276-95d6-2e09d87b5546"
    );
  });

  it("renders recording pin events", async () => {
    queryClient.setQueryData(queryKey, {
      pages: [
        {
          events: timelineProps.events.filter(
            (event) => event.event_type === EventType.RECORDING_PIN
          ),
        },
      ],
      pageParams: [Date.now()],
    });

    renderWithProviders(
      <UserFeedPage />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      expect(queryClient.getQueryState(queryKey)?.status).toEqual("success");
    });
    const timeline = screen.getByTestId("timeline");
    expect(timeline).toBeInTheDocument();
    expect(within(timeline).getAllByRole("listitem")).toHaveLength(1);
    within(timeline).getByText(textContentMatcher("jdaok pinned a track"));
    within(timeline).getByText("Feb 16, 2021, 10:44 AM");
    within(timeline).getByText("Caroline Polachek");
    within(timeline).getByText("Very good...");
  });
});
