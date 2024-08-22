import * as React from "react";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { screen, waitFor } from "@testing-library/react";
import { SetupServerApi, setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import UserDailyActivity, {
  UserDailyActivityProps,
} from "../../../src/user/stats/components/UserDailyActivity";
import * as userDailyActivityResponse from "../../__mocks__/userDailyActivity.json";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

const props: UserDailyActivityProps = {
  user: {
    name: "foobar",
  },
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
const queryKey = ["userDailyActivity", props.user.name, "week"];

const reactQueryWrapper = ({ children }: any) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

// Set timeZone to UTC+5:30 because the testdata is in that format
// eslint-disable-next-line no-extend-native
Date.prototype.getTimezoneOffset = () => -330;

describe("UserDailyActivity", () => {
  let server: SetupServerApi;
  beforeAll(async () => {
    const handlers = [
      http.get("/1/stats/user/foobar/daily-activity", async (path) => {
        return HttpResponse.json(userDailyActivityResponse);
      }),
    ];
    server = setupServer(...handlers);
    server.listen();
  });
  afterEach(() => {
    queryClient.cancelQueries();
    queryClient.clear();
  });
  it("renders correctly", async () => {
    renderWithProviders(
      <UserDailyActivity {...props} />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    expect(screen.getByTestId("user-daily-activity")).toBeInTheDocument();
  });

  it("displays error message when API call fails", async () => {
    const errorMessage = "API Error";

    queryClient.ensureQueryData({
      queryKey,
      queryFn: () => {
        return {
          data: {},
          hasError: true,
          errorMessage,
        };
      },
    });

    renderWithProviders(
      <UserDailyActivity {...props} />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );
    await waitFor(() => {
      expect(screen.getByTestId("user-daily-activity")).toBeInTheDocument();
    });

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(screen.queryByTestId("heatmap")).not.toBeInTheDocument();
  });

  it("renders heatmap with processed data", async () => {
    queryClient.ensureQueryData({
      queryKey,
      queryFn: () => {
        return {
          data: userDailyActivityResponse,
          hasError: false,
          errorMessage: "",
        };
      },
    });

    renderWithProviders(
      <UserDailyActivity {...props} />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      expect(screen.getByTestId("heatmap")).toBeInTheDocument();
    });

    const heatmap = screen.getByTestId("heatmap");
    // eslint-disable-next-line testing-library/no-node-access
    expect(heatmap.querySelectorAll("g")).toHaveLength(227);
  });
});
