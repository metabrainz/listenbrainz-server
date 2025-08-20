import * as React from "react";
import { screen, waitFor, act } from "@testing-library/react";
import { SetupServerApi, setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ArtistEvolutionStreamGraph, {
  UserArtistEvolutionProps,
} from "../../../src/user/stats/components/UserArtistEvolutionActivity";
import * as userArtistEvolutionResponse from "../../__mocks__/userArtistEvolutionActivity.json";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

const userProps: UserArtistEvolutionProps = {
  user: {
    name: "foobar",
  },
  range: "week",
};

jest.mock("@nivo/stream", () => ({
  ...jest.requireActual("@nivo/stream"),
  ResponsiveStream: ({ children }: any) =>
    children ? children({ width: 400, height: 400 }) : <div>Mock Stream Chart</div>,
}));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      staleTime: 0,
      gcTime: 0, // Changed from cacheTime to gcTime (React Query v4+)
    },
  },
});

const reactQueryWrapper = ({ children }: any) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe("ArtistEvolutionStreamGraph", () => {
  let server: SetupServerApi;
  
  beforeAll(() => {
    const handlers = [
      // Fixed: Use the correct endpoint that matches the API calls
      http.get("/1/stats/user/foobar/artist-evolution-activity", async ({ request }) => {
        const url = new URL(request.url);
        const range = url.searchParams.get("range");

        switch (range) {
          case "week":
            return HttpResponse.json(userArtistEvolutionResponse);
          case "empty":
            return HttpResponse.json({
              result: [],
              offset_year: 2020,
            });
          case "month":
            // This will trigger the error case
            return HttpResponse.json(
              { message: "Failed to fetch data" },
              { status: 500 }
            );
          default:
            return HttpResponse.json(userArtistEvolutionResponse);
        }
      }),
    ];
    server = setupServer(...handlers);
    server.listen({ onUnhandledRequest: 'error' });
  });

  beforeEach(() => {
    queryClient.clear();
  });

  afterEach(() => {
    queryClient.cancelQueries();
    server.resetHandlers();
  });

  afterAll(() => {
    server.close();
  });

  it("renders correctly", async () => {
    await act(async () => {
      renderWithProviders(
        <ArtistEvolutionStreamGraph {...userProps} />, 
        {},
        { wrapper: reactQueryWrapper }
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("artist-evolution")).toBeInTheDocument();
    });
  });

  it("displays error message when API call fails", async () => {
    await act(async () => {
      renderWithProviders(
        <ArtistEvolutionStreamGraph {...{ ...userProps, range: "month" }} />, 
        {},
        { wrapper: reactQueryWrapper }
      );
    });

    await waitFor(() => {
      // The component shows an error icon when API call fails
      const errorIcon = screen.getByRole('img', { hidden: true });
      expect(errorIcon).toHaveAttribute('data-icon', 'circle-exclamation');
    }, { timeout: 8000 });
  }, 15000);

  it("displays no data message when chart data is empty", async () => {
    // Override the server handler for this specific test
    server.use(
      http.get("/1/stats/user/foobar/artist-evolution-activity", async ({ request }) => {
        const url = new URL(request.url);
        const range = url.searchParams.get("range");
        
        if (range === "week") {
          return HttpResponse.json({
            result: [],
            offset_year: 2020,
          });
        }
        
        return HttpResponse.json(userArtistEvolutionResponse);
      })
    );
  
    await act(async () => {
      renderWithProviders(
        <ArtistEvolutionStreamGraph {...userProps} />, // Uses "week" range
        {},
        { wrapper: reactQueryWrapper }
      );
    });
  
    await waitFor(() => {
      expect(screen.getByText("No artist evolution data available for this time period")).toBeInTheDocument();
    }, { timeout: 8000 });
  }, 15000);
});