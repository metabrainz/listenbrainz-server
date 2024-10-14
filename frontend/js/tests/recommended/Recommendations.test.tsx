import * as React from "react";

import { Router } from "@remix-run/router";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import * as recommendationProps from "../__mocks__/recommendations.json";

import getRecommendationsRoutes from "../../src/recommended/tracks/routes";
import {
  renderWithProviders,
  textContentMatcher,
} from "../test-utils/rtl-test-utils";
import { RecommendationsProps } from "../../src/recommended/tracks/Recommendations";

const { recommendations, user: userProp, lastUpdated } = recommendationProps;

const user = userEvent.setup();

const routes = getRecommendationsRoutes();

const fetchedProps: RecommendationsProps = {
  recommendations,
  user: userProp,
  lastUpdated,
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});
const queryKey = ["recommendation", { userName: userProp.name }, {}];
// preload data
queryClient.ensureQueryData({ queryKey, queryFn: () => fetchedProps });

const reactQueryWrapper = ({ children }: any) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe("Recommendations", () => {
  let router: Router;
  let server: SetupServerApi;
  const recAPIFeedbackSpy = jest.fn();
  beforeAll(async () => {
    window.HTMLElement.prototype.scrollIntoView = jest.fn();

    const handlers = [
      http.post("/recommended/tracks/vansika/raw/", ({ request }) => {
        return HttpResponse.json(fetchedProps);
      }),
      http.get("/1/recommendation/feedback/user/vansika/*", ({ request }) => {
        recAPIFeedbackSpy();
        return HttpResponse.json({
          count: 2,
          feedback: [
            {
              created: 1634807734,
              rating: "hate",
              recording_mbid: "7ff2815b-2461-4c95-8497-a2476c631c5d",
            },
            {
              created: 1611223134,
              rating: "love",
              recording_mbid: "24a7952a-c435-4b7b-8c57-f346b4a29f9f",
            },
          ],
          offset: 0,
          total_count: 2,
          user_name: "vansika",
        });
      }),
    ];
    server = setupServer(...handlers);
    server.listen();
    // Create the router *after* MSW mock server is set up
    // See https://github.com/mswjs/msw/issues/1653#issuecomment-1781867559
    router = createMemoryRouter(routes, {
      initialEntries: ["/recommended/tracks/vansika/raw/"],
    });

  });

  afterEach(jest.clearAllMocks);

  afterAll(() => {
    queryClient.cancelQueries();
    server.close();
  });

  it("renders correctly on the recommendations page", async () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      undefined,
      { wrapper: reactQueryWrapper },
      false
    );
    screen.getByText("vansika");
    await waitFor(() => {
      // Wait for data to be successfully loaded
      const state = queryClient.getQueryState(queryKey);
      expect(state?.status === "success").toBeTruthy();
    });
    screen.getByText(
      textContentMatcher(
        "Your raw tracks playlist was last updated on 20 May 2024."
      )
    );
    screen.getByTestId("recommendations");
    screen.getByTestId("recommendations-table");
    await waitFor(() => {
      expect(screen.getAllByTestId("listen")).toHaveLength(25);
    });
    screen.getByText("Gila Monster");
  });

  it('calls loadFeedback if user is the currentUser"', async () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {
        currentUser: recommendationProps.user,
      },
      {wrapper: reactQueryWrapper},
      false
    );
    await waitFor(() => {
      // Wait for data to be successfully loaded
      const state = queryClient.getQueryState(queryKey);
      expect(state?.status === "success").toBeTruthy();
    });
    expect(recAPIFeedbackSpy).toHaveBeenCalledTimes(1);
  });

  it("does not call loadFeedback if user is not the currentUser", async () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {
        currentUser: { name: "tarzan" },
      },
      {wrapper: reactQueryWrapper},
      false
    );
    await waitFor(() => {
      // Wait for data to be successfully loaded
      const state = queryClient.getQueryState(queryKey);
      expect(state?.status === "success").toBeTruthy();
    });
    // Ensure feedback elements are not present
    expect(recAPIFeedbackSpy).not.toHaveBeenCalled();
  });

  /* it("updates the recommendation feedback when clicked", async () => {
    renderWithProviders(
    <RouterProvider router={router} />,
    {
      currentUser: recommendationProps.user,
    },
    undefined,
    false
  );
    // Ensure feedback elements are not present for a certain track
    // const recommendationFeedbackMap: RecommendationFeedbackMap = {
    //   "973e5620-829d-46dd-89a8-760d87076287": "like",
    // };
    // Defined a server handler for the feedback update endpoint
    // Then click on a feedback button
    // Then check that the feedback has changed
  }); */

  it("has working navigation", async () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      undefined,
      { wrapper: reactQueryWrapper },
      false
    );
    await waitFor(() => {
      // Wait for data to be successfully loaded
      const state = queryClient.getQueryState(queryKey);
      expect(state?.status).toEqual("success");
    });
    const trackFromFirstPage = recommendations[0].track_metadata.track_name;
    const trackFromSecondPage = recommendations[25].track_metadata.track_name;
    const trackFromThirdPage = recommendations[50].track_metadata.track_name;
    // First page
    screen.getByText(trackFromFirstPage);
    expect(screen.queryByText(trackFromSecondPage)).toBeNull();
    expect(screen.queryByText(trackFromThirdPage)).toBeNull();

    const navButtons = screen.getByRole("navigation");
    const nextButton = within(navButtons).getByText("Next", { exact: false });
    // Second page
    await user.click(nextButton);
    screen.getByText(trackFromSecondPage);
    expect(screen.queryByText(trackFromFirstPage)).toBeNull();
    expect(screen.queryByText(trackFromThirdPage)).toBeNull();

    // Third page
    await user.click(nextButton);
    screen.getByText(trackFromThirdPage);
    expect(screen.queryByText(trackFromFirstPage)).toBeNull();
    expect(screen.queryByText(trackFromSecondPage)).toBeNull();
    // No fourth page, should do nothing
    await user.click(nextButton);
    screen.getByText(trackFromThirdPage);
    expect(screen.queryByText(trackFromFirstPage)).toBeNull();
    expect(screen.queryByText(trackFromSecondPage)).toBeNull();

    const prevButton = within(navButtons).getByText("Previous", {
      exact: false,
    });
    // Second page
    await user.click(prevButton);
    screen.getByText(trackFromSecondPage);
    expect(screen.queryByText(trackFromFirstPage)).toBeNull();
    expect(screen.queryByText(trackFromThirdPage)).toBeNull();
    // First page
    await user.click(prevButton);
    screen.getByText(trackFromFirstPage);
    expect(screen.queryByText(trackFromSecondPage)).toBeNull();
    expect(screen.queryByText(trackFromThirdPage)).toBeNull();
    // clicking again should do nothing
    await user.click(prevButton);
    screen.getByText(trackFromFirstPage);
    expect(screen.queryByText(trackFromSecondPage)).toBeNull();
    expect(screen.queryByText(trackFromThirdPage)).toBeNull();
  });
});
