import * as React from "react";
import { mount } from "enzyme";

import BrainzPlayerUI from "../../src/brainzplayer/BrainzPlayerUI";

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
  newAlert: (): any => {},
};
describe("BrainzPlayerUI", () => {
  it("renders", () => {
    const wrapper = mount(<BrainzPlayerUI {...props} />);
    expect(wrapper).toMatchSnapshot();
  });
});
