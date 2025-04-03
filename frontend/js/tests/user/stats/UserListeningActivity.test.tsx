import * as React from "react";

import { ResponsiveBar } from "@nivo/bar";
import { Context as ResponsiveContext } from "react-responsive";
import { screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SetupServerApi, setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import UserListeningActivity, {
  UserListeningActivityProps,
} from "../../../src/user/stats/components/UserListeningActivity";
import * as userListeningActivityResponseWeek from "../../__mocks__/userListeningActivityWeek.json";
import * as userListeningActivityResponseMonth from "../../__mocks__/userListeningActivityMonth.json";
import * as userListeningActivityResponseYear from "../../__mocks__/userListeningActivityYear.json";
import * as userListeningActivityResponseAllTime from "../../__mocks__/userListeningActivityAllTime.json";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

const userProps: UserListeningActivityProps = {
  user: {
    name: "foobar",
  },
  range: "week",
};

const sitewideProps: UserListeningActivityProps = {
  range: "week",
};

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

const setQueryData = (
  userName: string | undefined,
  range: string,
  data: any
) => {
  const queryKey = ["userListeningActivity", userName, range];
  queryClient.ensureQueryData({
    queryKey,
    queryFn: () => {
      return data;
    },
  });
};

const getResponse = (range: string) => {
  let response;
  switch (range) {
    case "week":
      response = userListeningActivityResponseWeek;
      break;
    case "month":
      response = userListeningActivityResponseMonth;
      break;
    case "year":
      response = userListeningActivityResponseYear;
      break;
    case "all_time":
      response = userListeningActivityResponseAllTime;
      break;
    default:
      response = {};
  }
  return HttpResponse.json(response);
};

describe.each([
  ["User Stats", userProps],
  ["Sitewide Stats", sitewideProps],
])("%s", (name, props) => {
  let server: SetupServerApi;
  beforeAll(async () => {
    const handlers = [
      http.get(
        "/1/stats/user/foobar/listening-activity",
        async ({ request }) => {
          const url = new URL(request.url);
          const range = url.searchParams.get("range");
          return getResponse(range as string);
        }
      ),
      http.get("/1/stats/sitewide/listening-activity", async ({ request }) => {
        const url = new URL(request.url);
        const range = url.searchParams.get("range");
        return getResponse(range as string);
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
  it("renders correctly for week", async () => {
    setQueryData(props.user?.name, "week", {
      data: userListeningActivityResponseWeek,
      hasError: false,
      errorMessage: "",
    });

    renderWithProviders(
      <ResponsiveContext.Provider value={{ width: 700 }}>
        <UserListeningActivity {...props} />
      </ResponsiveContext.Provider>,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      expect(screen.getByTestId("listening-activity-bar")).toBeInTheDocument();
    });

    expect(screen.getByTestId("listening-activity")).toBeInTheDocument();

    // Expect the total listens and average listens per day to be displayed
    expect(screen.getByText("141")).toBeInTheDocument();
    expect(screen.getByText("21")).toBeInTheDocument();
  });

  it("renders correctly for month", async () => {
    setQueryData(props.user?.name, "month", {
      data: userListeningActivityResponseMonth,
      hasError: false,
      errorMessage: "",
    });

    renderWithProviders(
      <ResponsiveContext.Provider value={{ width: 700 }}>
        <UserListeningActivity {...{ ...props, range: "month" }} />
      </ResponsiveContext.Provider>,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      expect(screen.getByTestId("listening-activity-bar")).toBeInTheDocument();
    });

    expect(screen.getByTestId("listening-activity")).toBeInTheDocument();

    // Expect the total listens and average listens per day to be displayed
    expect(screen.getByText("359")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
  });

  it("renders correctly for year", async () => {
    setQueryData(props.user?.name, "year", {
      data: userListeningActivityResponseYear,
      hasError: false,
      errorMessage: "",
    });

    renderWithProviders(
      <ResponsiveContext.Provider value={{ width: 800 }}>
        <UserListeningActivity {...{ ...props, range: "year" }} />
      </ResponsiveContext.Provider>,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      expect(screen.getByTestId("listening-activity-bar")).toBeInTheDocument();
    });

    expect(screen.getByTestId("listening-activity")).toBeInTheDocument();

    // Expect the total listens and average listens per month to be displayed
    expect(screen.getByText("3580")).toBeInTheDocument();
    expect(screen.getByText("597")).toBeInTheDocument();
  });

  it("renders correctly for all_time", async () => {
    setQueryData(props.user?.name, "all_time", {
      data: userListeningActivityResponseAllTime,
      hasError: false,
      errorMessage: "",
    });

    renderWithProviders(
      <ResponsiveContext.Provider value={{ width: 800 }}>
        <UserListeningActivity {...{ ...props, range: "all_time" }} />
      </ResponsiveContext.Provider>,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      expect(screen.getByTestId("listening-activity-bar")).toBeInTheDocument();
    });

    expect(screen.getByTestId("listening-activity")).toBeInTheDocument();

    // Expect the total listens and average listens per year to be displayed
    expect(screen.getByText("3845")).toBeInTheDocument();
    expect(screen.getByText("161")).toBeInTheDocument();
  });

  it("displays error message when API call fails", async () => {
    const errorMessage = "API Error";
    setQueryData(props.user?.name, "week", {
      data: {},
      hasError: true,
      errorMessage,
    });
    renderWithProviders(
      <ResponsiveContext.Provider value={{ width: 800 }}>
        <UserListeningActivity {...props} />
      </ResponsiveContext.Provider>,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      expect(screen.getByTestId("error-message")).toBeInTheDocument();
    });

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });
});
