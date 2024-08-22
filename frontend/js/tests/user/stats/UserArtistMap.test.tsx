import * as React from "react";

import { screen, waitFor } from "@testing-library/react";
import { SetupServerApi, setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import UserArtistMap, {
  UserArtistMapProps,
} from "../../../src/user/stats/components/UserArtistMap";
import * as userArtistMapResponse from "../../__mocks__/userArtistMap.json";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

const userProps: UserArtistMapProps = {
  user: {
    name: "foobar",
  },
  range: "week",
};

const sitewideProps: UserArtistMapProps = {
  range: "week",
};

jest.mock("@nivo/core", () => ({
  ...jest.requireActual("@nivo/core"),
  ResponsiveWrapper: ({ children }: any) =>
    children({ width: 400, height: 400 }),
}));

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

describe.each([
  ["User Stats", userProps],
  ["Sitewide Stats", sitewideProps],
])("%s", (name, props) => {
  let server: SetupServerApi;
  beforeAll(async () => {
    const handlers = [
      http.get("/1/stats/user/foobar/artist-map", async ({ request }) => {
        const url = new URL(request.url);
        const range = url.searchParams.get("range");

        switch (range) {
          case "week":
            return HttpResponse.json(userArtistMapResponse);
          default:
            return HttpResponse.json(
              { error: "Failed to fetch data" },
              { status: 500 }
            );
        }
      }),
      http.get("/1/stats/sitewide/artist-map", async ({ request }) => {
        const url = new URL(request.url);
        const range = url.searchParams.get("range");

        switch (range) {
          case "week":
            return HttpResponse.json(userArtistMapResponse);
          default:
            return HttpResponse.json(
              { error: "Failed to fetch data" },
              { status: 500 }
            );
        }
      }),
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
      <UserArtistMap {...props} />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    // Wait for loading to finish
    await waitFor(() => {
      expect(screen.getByTestId("Choropleth")).toBeInTheDocument();
    });

    expect(screen.getByTestId("user-stats-map")).toBeInTheDocument();
  });

  it("displays error message when API call fails", async () => {
    renderWithProviders(
      <UserArtistMap {...{ ...props, range: "month" }} />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    // Wait for loading to finish
    await waitFor(() => {
      expect(screen.getByTestId("error-message")).toBeInTheDocument();
    });

    expect(screen.getByText("Failed to fetch data")).toBeInTheDocument();
    expect(screen.queryByTestId("Choropleth")).not.toBeInTheDocument();
  });

  it("renders choropleth with processed data", async () => {
    renderWithProviders(
      <UserArtistMap {...props} />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    // Wait for loading to finish
    await waitFor(() => {
      expect(screen.getByTestId("Choropleth")).toBeInTheDocument();
    });

    // Check if the choropleth is rendered correctly
    const choropleth = screen.getByTestId("Choropleth");
    // eslint-disable-next-line testing-library/no-node-access
    expect(choropleth.querySelectorAll("g")).toHaveLength(8);
  });
});
