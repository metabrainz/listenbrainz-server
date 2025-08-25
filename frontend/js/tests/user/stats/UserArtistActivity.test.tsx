// frontend/js/tests/user/stats/UserArtistEvolutionActivity.test.tsx
import * as React from "react";
import { screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import GlobalAppContext from "../../../src/utils/GlobalAppContext";
import ArtistEvolutionActivityStreamGraph from "../../../src/user/stats/components/UserArtistEvolutionActivity";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

type Props = React.ComponentProps<typeof ArtistEvolutionActivityStreamGraph>;

const userProps: Props = {
  user: { name: "foobar" } as any,
  range: "year" as UserStatsAPIRange,
};

const sitewideProps: Props = {
  range: "year" as UserStatsAPIRange,
};

// Mock the Nivo stream chart to avoid rendering a heavy SVG tree
jest.mock("@nivo/stream", () => ({
  ResponsiveStream: () => <div>Mock Stream Chart</div>,
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const reactQueryWrapper = ({ children }: any) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

function withProviders(
  ui: React.ReactElement,
  APIService: any,
) {
  return renderWithProviders(
    <GlobalAppContext.Provider value={{ APIService } as any}>
      {ui}
    </GlobalAppContext.Provider>,
    {},
    { wrapper: reactQueryWrapper }
  );
}

// Base payload shape the component expects
const basePayload = {
  offset_year: 2020,
  range: "year" as UserStatsAPIRange,
  from_ts: 0,
  to_ts: 0,
  last_updated: 0,
  user_id: "foobar",
};

describe.each([
  ["User Stats", userProps],
  ["Sitewide Stats", sitewideProps],
])("%s", (_name, props) => {
  afterEach(() => {
    queryClient.cancelQueries();
    queryClient.clear();
    jest.clearAllMocks();
  });

  it("renders the chart when API returns data", async () => {
    const APIService = {
      getUserArtistEvolutionActivity: jest.fn().mockResolvedValue({
        payload: {
          ...basePayload,
          range: props.range,
          artist_evolution_activity: [
            { id: "Jan", "Artist A": 5, "Artist B": 2 },
            { id: "Feb", "Artist A": 3, "Artist B": 4 },
          ],
        },
      } as UserArtistEvolutionActivityResponse),
    };

    withProviders(<ArtistEvolutionActivityStreamGraph {...props} />, APIService);

    // Mocked chart should render and empty-state should NOT be present
    await waitFor(() => {
      expect(screen.getByText("Mock Stream Chart")).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("artist-evolution-stream")
    ).toBeInTheDocument();
    expect(
      screen.queryByText("No artist evolution data available for this time period")
    ).not.toBeInTheDocument();
  });

  it("shows error message when API call fails", async () => {
    const APIService = {
      getUserArtistEvolutionActivity: jest
        .fn()
        .mockRejectedValue(new Error("Failed to fetch data")),
    };

    withProviders(<ArtistEvolutionActivityStreamGraph {...props} />, APIService);

    await waitFor(() => {
      expect(screen.getByText("Failed to fetch data")).toBeInTheDocument();
    });
  });
});
