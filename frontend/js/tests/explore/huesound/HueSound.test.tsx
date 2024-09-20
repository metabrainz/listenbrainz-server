/* eslint-disable jest/no-disabled-tests */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import * as React from "react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import HueSound from "../../../src/explore/huesound/HueSound";
import {
  renderWithProviders,
  textContentMatcher,
} from "../../test-utils/rtl-test-utils";
import getExploreRoutes from "../../../src/explore/routes";
import { ReactQueryWrapper } from "../../test-react-query";

const release: ColorReleaseItem = {
  artist_name: "Rorcal & Music For The Space",
  caa_id: 19203085767,
  color: [0, 0, 0],
  dist: 0,
  recordings: [
    {
      listened_at: 0,
      track_metadata: {
        additional_info: {
          artist_mbids: [
            "27030b71-0eb7-4dc9-93f5-6f43b9970d73",
            "015ef401-99cf-4d84-a8b7-ccb141067c53",
          ],
          recording_mbid: "41abe69a-4f82-4b48-ac56-4a43de2b57d9",
          release_mbid: "18f6bbb8-16b3-4e0d-823d-dc2c13ee9bed",
        },
        artist_name: "Rorcal & Music For The Space",
        release_name: "Prelude to Heliogabalus",
        track_name: "Prelude to Heliogabalus",
      },
    },
  ],
  release_mbid: "18f6bbb8-16b3-4e0d-823d-dc2c13ee9bed",
  release_name: "Prelude to Heliogabalus",
};
jest.unmock("react-toastify");

const user = userEvent.setup();

const exploreRoutes = getExploreRoutes();

const memRouter = createMemoryRouter(exploreRoutes, {
  // Pretend we just navigated to a specific color,
  // because we can't interact with the colorwheel canvas element to select one
  initialEntries: ["/explore/huesound/123321"],
});

describe("HueSound", () => {
  let server: SetupServerApi;
  beforeAll(async () => {
    // Mock the server responses
    const handlers = [
      http.get("/1/explore/color/123321", () =>
        HttpResponse.json({ payload: { releases: [release] } })
      ),
    ];
    server = setupServer(...handlers);
    server.listen();
  });
  afterAll(() => {
    server.close();
  });

  it("contains a ColorWheel instance", () => {
    renderWithProviders(<HueSound />);
    screen.getByTestId("colour-picker");
    // screen.getByText();
    expect(screen.getAllByRole("heading").at(2)).toHaveTextContent(
      "Choose a coloron the wheel!"
    );
  });

  it("renders a release when a color is passed in URL", async () => {
    // With initial navigation, see initialEntries when we create memRouter
    render(<RouterProvider router={memRouter} />);

    await screen.findByText(
      textContentMatcher("Click an album cover to start playing!")
    );
    await waitFor(() => {
      const releaseButton = screen.getByRole("button");
      within(releaseButton).getByAltText(
        "Cover art for Release Prelude to Heliogabalus"
      );
    });
  });

  it("renders a release and plays it when selected", async () => {
    const messages: MessageEvent[] = [];
    window.addEventListener("message", (message: MessageEvent) =>
      messages.push(message)
    );
    // With initial navigation, see initialEntries when we create memRouter
    renderWithProviders(
      <RouterProvider router={memRouter} />,
      {},
      {
        wrapper: ReactQueryWrapper,
      },
      false
    );

    await waitFor(async () => {
      const releaseButton = screen.getByRole("button");
      await user.click(releaseButton);
    });
    const mainContent = screen.getByRole("main");
    const links = within(mainContent).getAllByRole("link");
    expect(links.at(0)).toHaveTextContent("Prelude to Heliogabalus");
    expect(links.at(1)).toHaveTextContent("Rorcal & Music For The Space");

    const brainzPlayerMessages = messages.filter(
      (m) => m.data.brainzplayer_event
    );
    expect(brainzPlayerMessages).toHaveLength(1);
    expect(brainzPlayerMessages[0].data.brainzplayer_event).toEqual(
      "play-listen"
    );
  });
});
