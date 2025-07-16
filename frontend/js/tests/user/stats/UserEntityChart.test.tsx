import * as React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import fetchMock from "jest-fetch-mock";

import UserEntityChart, {
  UserEntityChartProps,
} from "../../../src/user/charts/UserEntityChart";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import APIService from "../../../src/utils/APIService";
import userArtistsResponse from "../../__mocks__/userArtists.json";
import userArtistsProcessDataOutput from "../../__mocks__/userArtistsProcessData.json";

import userReleaseGroupsResponse from "../../__mocks__/userReleaseGroups.json";
import userRecordingsResponse from "../../__mocks__/userRecordings.json";
import userReleasesResponse from "../../__mocks__/userReleases.json";
import { queryClient, ReactQueryWrapper } from "../../test-react-query";
import * as utils from "../../../src/user/charts/utils";

// Polyfill for AbortController to prevent "Expected signal to be an instance of AbortSignal" error in JSDOM
if (typeof AbortController === "undefined") {
  global.AbortController = class AbortController {
    signal = {
      aborted: false,
      addEventListener: () => {},
      removeEventListener: () => {},
      reason: undefined,
      onabort: null,
      throwIfAborted: () => {},
    };
    abort() {
      // @ts-ignore
      this.signal.aborted = true;
    }
  } as any;
}

fetchMock.enableMocks();

// Mock child components
jest.mock("../../../src/user/charts/components/Bar", () => () => (
  <div data-testid="bar-chart" />
));
jest.mock("../../../src/common/listens/ListenCard", () => () => (
  <div data-testid="listen" />
));
jest.mock(
  "../../../src/explore/fresh-releases/components/ReleaseCard",
  () => () => <div data-testid="release-card" />
);
jest.mock(
  "../../../src/components/Loader",
  () => ({ isLoading, children }: any) =>
    isLoading ? <div data-testid="loader" /> : children
);

const mockUser: ListenBrainzUser = {
  id: 1,
  name: "test-user",
};

const defaultLoaderData: UserEntityChartProps = {
  user: mockUser,
  entity: "artist",
  terminology: "artist",
  range: "all_time",
  currPage: 1,
};

const mockAPIService = new APIService("");
const getUserEntitySpy = jest
  .spyOn(mockAPIService, "getUserEntity")
  .mockResolvedValue(userArtistsResponse as UserEntityResponse);

const defaultContext: Partial<GlobalAppContextT> = {
  APIService: mockAPIService,
  currentUser: mockUser,
};

// Helper to render the component within a react-router context
const renderComponent = (loaderData: Partial<UserEntityChartProps> = {}) => {
  const mergedLoaderData = { ...defaultLoaderData, ...loaderData };
  const router = createMemoryRouter(
    [
      {
        path: "/user/:username/stats/",
        children: [
          {
            path: "*",
            element: <UserEntityChart />,
            loader: () => mergedLoaderData,
            hydrateFallbackElement: <p>Initial Load</p>,
          },
        ],
      },
    ],
    {
      initialEntries: ["/", "/user/test-user/stats/top-artists/"],
      initialIndex: 1,
    }
  );

  return {
    ...render(
      <GlobalAppContext.Provider value={defaultContext as GlobalAppContextT}>
        <ReactQueryWrapper>
          <RouterProvider router={router} />
        </ReactQueryWrapper>
      </GlobalAppContext.Provider>,
      { hydrate: false }
    ),
    // Also return the router so we can check its state (for testing navigation)
    router,
  };
};

describe("UserEntityChart", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    queryClient.cancelQueries();
  });

  const testCases = [
    {
      entity: "artist",
      terminology: "artist",
      expectedHeading: /Top artists of all time/i,
      mockData: userArtistsResponse,
      expectedCardTestID: "listen",
    },
    {
      entity: "release",
      terminology: "album",
      expectedHeading: /Top albums of all time/i,
      mockData: userReleasesResponse,
      expectedCardTestID: "release-card",
    },
    {
      entity: "release-group",
      terminology: "album",
      expectedHeading: /Top albums of all time/i,
      mockData: userReleaseGroupsResponse,
      expectedCardTestID: "release-card",
    },
    {
      entity: "recording",
      terminology: "track",
      expectedHeading: /Top tracks of all time/i,
      mockData: userRecordingsResponse,
      expectedCardTestID: "listen",
    },
  ];

  it.each(testCases)(
    "renders correctly for $terminology",
    async ({
      entity,
      terminology,
      expectedHeading,
      mockData,
      expectedCardTestID,
    }) => {
      getUserEntitySpy.mockResolvedValueOnce(mockData as UserEntityResponse);

      renderComponent({
        entity: entity as Entity,
        terminology: terminology as any,
      });

      await waitFor(() => {
        expect(screen.getByTestId("loader")).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(screen.queryByTestId("loader")).not.toBeInTheDocument();
      });
      expect(getUserEntitySpy).toHaveBeenCalledTimes(1);

      await waitFor(() => {
        expect(
          screen.getByRole("heading", { name: expectedHeading, level: 3 })
        ).toBeInTheDocument();
        expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
        // Use getAllByTestId to ensure at least one card is rendered
        expect(
          screen.getAllByTestId(expectedCardTestID)[0]
        ).toBeInTheDocument();
      });
    }
  );

  it("displays an error message when data fetching fails", async () => {
    const errorMessage = "Failed to fetch data";
    getUserEntitySpy.mockRejectedValueOnce(new Error(errorMessage));
    renderComponent();

    await waitFor(() => {
      expect(screen.queryByTestId("loader")).not.toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
      expect(screen.queryByTestId("bar-chart")).not.toBeInTheDocument();
    });
  });

  it("navigates when a different entity pill is clicked", async () => {
    const { router } = renderComponent();
    getUserEntitySpy.mockResolvedValueOnce(
      userArtistsResponse as UserEntityResponse
    );

    await waitFor(() => {
      expect(screen.queryByTestId("loader")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.queryByTestId("loader")).not.toBeInTheDocument();
    });

    expect(router.state.location.pathname).toEqual(
      "/user/test-user/stats/top-artists/"
    );

    const albumsPill = screen.getByRole("link", { name: "Albums" });
    expect(albumsPill).toHaveAttribute(
      "href",
      "/user/test-user/stats/top-albums/?range=all_time"
    );
    await fireEvent.click(albumsPill);

    await waitFor(() => {
      // We fuck around with the loaderData when creating the router
      // so clicking the link changes the route but not the actual loader data
      expect(router.state.location.pathname).toEqual(
        "/user/test-user/stats/top-albums/"
      );
    });
  });

  it("navigates to a new page when pagination is clicked", async () => {
    getUserEntitySpy.mockResolvedValueOnce(
      userArtistsResponse as UserEntityResponse
    );
    const { router } = renderComponent();

    await waitFor(() => {
      expect(screen.queryByTestId("loader")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.queryByTestId("loader")).not.toBeInTheDocument();
    });

    expect(router.state.location.search).toEqual("");

    screen.getByText(/page 1/);
    expect(screen.queryByRole("button", { name: "1" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Previous/ })).toHaveAttribute(
      "aria-disabled",
      "true"
    );
    expect(screen.getByRole("button", { name: /Next/ })).toHaveAttribute(
      "aria-disabled",
      "false"
    );
    const secondPageLink = screen.getByRole("button", { name: "2" });
    expect(secondPageLink).toHaveAttribute(
      // Check for page 2 search param
      "href",
      "/user/test-user/stats/top-artists/?page=2&range=all_time"
    );
    await fireEvent.click(secondPageLink);

    await waitFor(() => {
      // We fuck around with the loaderData when creating the router
      // so clicking the link changes the route but not the actual loader data
      expect(router.state.location.search).toEqual("?page=2&range=all_time");
    });
  });
});
