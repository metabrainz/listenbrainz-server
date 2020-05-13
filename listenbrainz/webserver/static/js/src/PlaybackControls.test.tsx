import * as React from "react";
import { mount } from "enzyme";

import PlaybackControls from "./PlaybackControls";

const props = {
  playPreviousTrack: () => {},
  playNextTrack: () => {},
  togglePlay: () => {},
  playerPaused: true,
  toggleDirection: () => {},
  direction: "up" as SpotifyPlayDirection,
  trackName: "Dangerous",
  artistName: "The xx",
  progressMs: 0,
  durationMs: 10000,
  seekToPositionMs: (msTimeCode: number) => {},
};
describe("PlaybackControls", () => {
  it("renders", () => {
    const wrapper = mount(<PlaybackControls {...props} />);
    expect(wrapper).toMatchSnapshot();
  });
});
