import * as React from "react";
import { mount } from "enzyme";

import { BrowserRouter } from "react-router-dom";
import BrainzPlayerUI from "../../../src/common/brainzplayer/BrainzPlayerUI";
import IntersectionObserver from "../../__mocks__/intersection-observer";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

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
    const wrapper = mount(
      <BrowserRouter>
        <BrainzPlayerUI {...props} />
      </BrowserRouter>
    );
    expect(wrapper.find("#brainz-player")).toHaveLength(1);
  });
});
