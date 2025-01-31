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
import FriendsFeedPage from "../../src/user-feed/FriendsFeed";
import * as timelineProps from "../__mocks__/listensTimelineProps.json";

import {
  renderWithProviders,
  textContentMatcher,
} from "../test-utils/rtl-test-utils";

jest.unmock("react-toastify");

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});
const queryKey = ["friends-feed", {}];

const reactQueryWrapper = ({ children }: any) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe("FriendsFeed", () => {
  let server: SetupServerApi;
  beforeAll(async () => {
    // Mock the server responses
    const handlers = [
      http.get(
        "http://localhost/1/user/*/feed/events/listens/following",
        async (path) => {
          // return feed events
          return HttpResponse.json({ payload: timelineProps });
        }
      ),
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
      <FriendsFeedPage />,
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

    const timeline = screen.getByTestId("listens");
    expect(timeline).toBeInTheDocument();
    expect(within(timeline).getAllByTestId("listen")).toHaveLength(
      timelineProps.events.length
    );

    expect(
      screen.getByText("What are my friends listening to?")
    ).toBeInTheDocument();
    // contains a UserSocialNetwork component
    expect(screen.getByText("Similar Users")).toBeInTheDocument();
    expect(
      screen.getByText("You aren't following anyone.")
    ).toBeInTheDocument();
  });

  it("has infinite pagination", async () => {
    renderWithProviders(
      <FriendsFeedPage />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      expect(queryClient.getQueryState(queryKey)?.data).toBeDefined();
    });

    const timeline = screen.getByTestId("listens");
    expect(timeline).toBeInTheDocument();
    expect(within(timeline).getAllByTestId("listen")).toHaveLength(
      timelineProps.events.length
    );

    const loadMoreButton = screen.getByText("Load More");
    const rightNow = Date.now();
    await userEvent.click(loadMoreButton);
    expect(
      queryClient.getQueryState(queryKey)?.dataUpdatedAt
    ).toBeGreaterThanOrEqual(rightNow);
  });

  it("renders listen events", async () => {
    renderWithProviders(
      <FriendsFeedPage />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      expect(queryClient.getQueryState(queryKey)?.status).toEqual("success");
    });
    const timeline = screen.getByTestId("listens");
    expect(timeline).toBeInTheDocument();
    expect(within(timeline).getAllByTestId("listen")).toHaveLength(2);
    screen.getByText("mr_monkey");
    screen.getByText("Psychlona");
    screen.getByText("Jasmine");
    screen.getByText("Jan 31, 2023, 4:05 PM");
    screen.getByText("reosarevok");
    screen.getByText("Kust on tulnud muodike");
    screen.getByText("Feb 16, 2021, 11:38 AM");
  });
});
