import * as React from "react";

import { BrowserRouter } from "react-router";
import BrainzPlayerUI from "../../../src/common/brainzplayer/BrainzPlayerUI";
import IntersectionObserver from "../../__mocks__/intersection-observer";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider as JotaiProvider, createStore } from "jotai";

const props = {
  playPreviousTrack: () => {},
  playNextTrack: () => {},
  togglePlay: () => {},
  playerPaused: true,
  trackName: "Dangerous",
  artistName: "The xx",
  progressMs: 0,
  durationMs: 10000,
  seekToPositionMs: (msTimeCode: number) => {},
  listenBrainzAPIBaseURI: "api.example.com",
  clearQueue: () => {},
};
describe("BrainzPlayerUI", () => {
  beforeAll(() => {
    global.IntersectionObserver = IntersectionObserver;
    window.HTMLElement.prototype.scrollIntoView = jest.fn();
  });
  it("renders", () => {
    render(
      <BrowserRouter>
        <BrainzPlayerUI {...props} />
      </BrowserRouter>
    );
    expect(screen.getByTestId("brainzplayer-ui")).toBeInTheDocument();
    expect(screen.getByTestId("queue")).toBeInTheDocument();
    // Main player bar buttons
    expect(screen.getByTestId("bp-previous-button")).toBeInTheDocument();
    expect(screen.getByTestId("bp-next-button")).toBeInTheDocument();
    expect(screen.getByTestId("bp-play-button")).toBeInTheDocument();
    // Mobile player UI buttons
    expect(screen.getByTestId("bp-mp-previous-button")).toBeInTheDocument();
    expect(screen.getByTestId("bp-mp-next-button")).toBeInTheDocument();
    expect(screen.getByTestId("bp-mp-play-button")).toBeInTheDocument();
  });

  it("hides the volume slider when the music player is minimised", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <JotaiProvider store={createStore()}>
        <BrowserRouter>
          <BrainzPlayerUI {...props} />
        </BrowserRouter>
      </JotaiProvider>
    );
    const volumeSlider = container.querySelector(".volume");
    const toggleMusicPlayer = container.querySelector(
      ".music-player .hide-queue"
    ) as Element;

    // Open the music player, then open the volume slider from it
    await user.click(toggleMusicPlayer);
    expect(container.querySelector(".music-player")).toHaveClass("open");
    await user.click(screen.getByRole("button", { name: "Volume" }));
    expect(volumeSlider).toHaveClass("show");

    // Minimising the music player should also hide the volume slider
    await user.click(toggleMusicPlayer);
    expect(container.querySelector(".music-player")).not.toHaveClass("open");
    expect(volumeSlider).not.toHaveClass("show");
  });
});
