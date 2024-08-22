import * as React from "react";

import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { HttpResponse, http } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import { screen, waitFor } from "@testing-library/react";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";
import UserReports from "../../../src/user/stats/UserReports";

const router = createMemoryRouter(
  [
    {
      path: "/user/:userName/stats",
      element: <UserReports />,
      loader: () => ({
        user: {
          name: "foobar",
        },
      }),
    },
  ],
  {
    initialEntries: ["/user/foobar/stats/?range=week"],
  }
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const reactQueryWrapper = ({ children }: any) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

const apiRoutes = [
  "/1/stats/user/foobar/listening-activity",
  "1/stats/user/foobar/artists",
  "/1/stats/user/foobar/release-groups",
  "/1/stats/user/foobar/recordings",
  "/1/stats/user/foobar/daily-activity",
  "/1/stats/user/foobar/artist-map",
];

let mockSearchParam = { range: "week" };
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useSearchParams: () => {
    const [params, setParams] = React.useState(
      new URLSearchParams(mockSearchParam)
    );
    return [
      params,
      (newParams: typeof mockSearchParam) => {
        mockSearchParam = newParams;
        setParams(new URLSearchParams(newParams));
      },
    ];
  },
}));

const user = userEvent.setup();

describe("UserReports", () => {
  let server: SetupServerApi;
  beforeAll(async () => {
    const handlers = apiRoutes.map((route) => {
      return http.get(route, async (path) => {
        return HttpResponse.json({});
      });
    });
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

  describe("UserReports", () => {
    it("Check if component is being rendered", () => {
      renderWithProviders(
        <RouterProvider router={router} />,
        {},
        {
          wrapper: reactQueryWrapper,
        },
        false
      );

      // Check if the component is rendered correctly
      expect(screen.getByTestId("User Reports")).toBeInTheDocument();

      // The week pill should be selected by default
      const weekPill = screen.getByTestId("range-week");
      expect(weekPill).toHaveClass("active");
    });

    it("should navigate on range change", async () => {
      renderWithProviders(
        <RouterProvider router={router} />,
        {},
        {
          wrapper: reactQueryWrapper,
        },
        false
      );

      const rangePill = screen.getByTestId("range-month");
      expect(rangePill).toBeInTheDocument();

      // Click on the month pill
      await user.click(rangePill);

      // Check if the month pill is selected
      expect(rangePill).toHaveClass("active");

      // Check if the URL is updated
      expect(mockSearchParam).toEqual({ range: "month" });

      // Check if new data is fetched
      const newQueryKey = ["user-top-entity", "artist", "month", "foobar"];
      await waitFor(() => {
        // Wait for data to be successfully loaded
        const state = queryClient.getQueryState(newQueryKey);
        expect(state?.status === "success").toBeTruthy();
      });
    });

    it("should navigate to week if invalid range is provided", async () => {
      mockSearchParam = { range: "invalid" };
      renderWithProviders(
        <RouterProvider router={router} />,
        {},
        {
          wrapper: reactQueryWrapper,
        },
        false
      );

      // Check if the URL is updated
      expect(mockSearchParam).toEqual({ range: "week" });
    });
  });
});
