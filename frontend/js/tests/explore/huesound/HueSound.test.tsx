/* eslint-disable jest/no-disabled-tests */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import * as React from "react";
import HueSound from "../../../src/explore/huesound/HueSound";
import {
  renderWithProviders,
  textContentMatcher,
} from "../../test-utils/rtl-test-utils";

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

describe("HueSound", () => {
  let server: SetupServerApi;
  beforeAll(async () => {
    // Mock the server responses
    const handlers = [
      http.get("/1/explore/color/000000", () =>
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

  it("renders a release when a color is selected", async () => {
    renderWithProviders(<HueSound />);

    const canvasElement = screen.getByTestId("colour-picker");
    await user.click(canvasElement);
    screen.getByText(
      textContentMatcher("Click an album cover to start playing!")
    );
    const releaseButton = screen.getByRole("button");
    within(releaseButton).getByAltText("Cover art for Release Prelude to Heliogabalus");
  });

  it("renders a release when one is selected", async () => {
    renderWithProviders(<HueSound />);

    const canvasElement = screen.getByTestId("colour-picker");
    await user.click(canvasElement);
    const releaseButton = screen.getByRole("button");
    await user.click(releaseButton);
    const links =  screen.getAllByRole("link");
    expect(links.at(0)).toHaveTextContent("Prelude to Heliogabalus")
    expect(links.at(1)).toHaveTextContent("Rorcal & Music For The Space")
  });
});
