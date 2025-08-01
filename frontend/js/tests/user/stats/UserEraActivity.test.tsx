import * as React from "react";

import { screen, waitFor } from "@testing-library/react";
import { SetupServerApi, setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import UserEraActivity, {
  UserEraActivityProps,
} from "../../../src/user/stats/components/UserEraActivity";
import * as userEraActivityResponse from "../../__mocks__/userEraActivity.json";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

const userProps: UserEraActivityProps = {
  user: {
    name: "foobar",
  },
  range: "all_time",
};

const sitewideProps: UserEraActivityProps = {
  range: "all_time",
};

jest.mock("@nivo/bar", () => ({
  ...jest.requireActual("@nivo/bar"),
  ResponsiveBar: ({ children }: any) => children({ width: 400, height: 400 }),
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
  beforeAll(() => {
    const handlers = [
      http.get("/1/stats/user/foobar/era-activity", async ({ request }) => {
        const url = new URL(request.url);
        const range = url.searchParams.get("range");

        switch (range) {
          case "week":
            return HttpResponse.json(userEraActivityResponse);
          default:
            return HttpResponse.json(
              { error: "Failed to fetch data" },
              { status: 500 }
            );
        }
      }),
      http.get("/1/stats/sitewide/era-activity", async ({ request }) => {
        const url = new URL(request.url);
        const range = url.searchParams.get("range");

        switch (range) {
          case "week":
            return HttpResponse.json(userEraActivityResponse);
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
      <UserEraActivity {...props} />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      expect(screen.getByTestId("user-era-activity")).toBeInTheDocument();
    });
  });

  it("displays error message when API call fails", async () => {
    renderWithProviders(
      <UserEraActivity {...{ ...props, range: "month" }} />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      expect(screen.getByText("Failed to fetch data")).toBeInTheDocument();
    });
  });

  it("displays Era Activity title", async () => {
    renderWithProviders(
      <UserEraActivity {...props} />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      expect(screen.getByText("Era Activity")).toBeInTheDocument();
    });
  });
});