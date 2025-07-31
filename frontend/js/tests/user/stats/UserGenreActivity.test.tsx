import * as React from "react";

import { screen, waitFor } from "@testing-library/react";
import { SetupServerApi, setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import UserGenreActivity, {
  UserGenreActivityProps,
} from "../../../src/user/stats/components/UserGenreActivity";
import * as userGenreDayActivityResponse from "../../__mocks__/userGenreActivity.json";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

const userProps: UserGenreActivityProps = {
  user: {
    name: "foobar",
  },
  range: "week",
};

jest.mock("@nivo/pie", () => ({
  ...jest.requireActual("@nivo/pie"),
  ResponsivePie: ({ children }: any) => children({ width: 400, height: 400 }),
}));

// Mock the useMediaQuery hook
jest.mock("../../../src/explore/fresh-releases/utils", () => ({
  useMediaQuery: jest.fn(() => false), // Default to desktop view
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

describe("User Stats", () => {
  let server: SetupServerApi;
  beforeAll(() => {
    const handlers = [
      http.get("/1/stats/user/foobar/genre-day-activity", async ({ request }) => {
        const url = new URL(request.url);
        const range = url.searchParams.get("range");

        switch (range) {
          case "week":
            return HttpResponse.json(userGenreDayActivityResponse);
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
      <UserGenreActivity {...userProps} />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      expect(screen.getByTestId("user-genre-activity")).toBeInTheDocument();
    });
  });

  it("displays error message when API call fails", async () => {
    renderWithProviders(
      <UserGenreActivity {...{ ...userProps, range: "month" }} />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );
	await waitFor(() => {
      expect(screen.getByText("Failed to fetch data")).toBeInTheDocument();
    });
  });

  it("renders time markers correctly", async () => {
    renderWithProviders(
      <UserGenreActivity {...userProps} />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );
	await waitFor(() => {
      expect(screen.getByText("12AM")).toBeInTheDocument();
	  expect(screen.getByText("6AM")).toBeInTheDocument();
	  expect(screen.getByText("12PM")).toBeInTheDocument();
      expect(screen.getByText("6PM")).toBeInTheDocument();
    });
  });

  it("displays Genre Activity title", async () => {
    renderWithProviders(
      <UserGenreActivity {...userProps} />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      expect(screen.getByText("Genre Activity")).toBeInTheDocument();
    });
  });
});