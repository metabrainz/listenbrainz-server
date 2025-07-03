import * as React from "react";

import { BrowserRouter } from "react-router";
import BrainzPlayerUI from "../../../src/common/brainzplayer/BrainzPlayerUI";
import IntersectionObserver from "../../__mocks__/intersection-observer";
import { render, screen } from "@testing-library/react";

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
});
