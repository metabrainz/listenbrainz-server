import * as React from "react";
import { screen, waitFor, act } from "@testing-library/react";
import { SetupServerApi, setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { ReactQueryWrapper, queryClient } from "../../test-react-query";
import ArtistEvolutionActivityStreamGraph, {
  UserArtistEvolutionActivityProps,
} from "../../../src/user/stats/components/UserArtistEvolutionActivity";
import * as userArtistEvolutionActivityResponse from "../../__mocks__/userArtistEvolutionActivity.json";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

const userProps: UserArtistEvolutionActivityProps = {
  user: { name: "foobar" },
  range: "week",
};

jest.mock("@nivo/stream", () => ({
  ...jest.requireActual("@nivo/stream"),
  ResponsiveStream: ({ children }: any) =>
    children ? children({ width: 400, height: 400 }) : <div>Mock Stream Chart</div>,
}));

describe("ArtistEvolutionActivityStreamGraph", () => {
  let server: SetupServerApi;

  beforeAll(() => {
    const handlers = [
      http.get("/1/stats/user/foobar/artist-evolution-activity", async ({ request }) => {
        const url = new URL(request.url);
        const range = url.searchParams.get("range");

        switch (range) {
          case "week":
            return HttpResponse.json(userArtistEvolutionActivityResponse);
          case "month":
            return HttpResponse.json({ message: "Failed to fetch data" }, { status: 500 });
          default:
            return HttpResponse.json(userArtistEvolutionActivityResponse);
        }
      }),
    ];
    server = setupServer(...handlers);
    server.listen({ onUnhandledRequest: "error" });
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
        <ArtistEvolutionActivityStreamGraph {...userProps} />, {}, { wrapper: ReactQueryWrapper }
      );
    });

    await screen.findByTestId("artist-evolution");
  });

  it("displays error message when API call fails", async () => {
    await act(async () => {
      renderWithProviders(
        <ArtistEvolutionActivityStreamGraph {...{ ...userProps, range: "month" }} />, {}, { wrapper: ReactQueryWrapper }
      );
    });

    await waitFor(
      () => {
        const errorIcon = screen.getByRole("img", { hidden: true });
        expect(errorIcon).toHaveAttribute("data-icon", "circle-exclamation");
    });
  });

  it("displays no data message when chart data is empty", async () => {
    server.use(
      http.get("/1/stats/user/foobar/artist-evolution-activity", async ({ request }) => {
        const url = new URL(request.url);
        const range = url.searchParams.get("range");
        if (range === "week") {
          return HttpResponse.json({
            payload: {
              artist_evolution_activity: [],
              range,
              from_ts: 0,
              to_ts: 0,
              last_updated: 0,
              user_id: "foobar",
            },
          });
        }
        return HttpResponse.json(userArtistEvolutionActivityResponse);
      })
    );

    await act(async () => {
      renderWithProviders(
        <ArtistEvolutionActivityStreamGraph {...userProps} />, {}, { wrapper: ReactQueryWrapper }
      );
    });

    await waitFor(
      () => {
        expect(
          screen.getByText("No artist evolution data available for this time period")
        ).toBeInTheDocument();
    });
  });
});