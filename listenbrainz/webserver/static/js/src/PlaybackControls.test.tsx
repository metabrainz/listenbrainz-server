import * as React from "react";
import { shallow } from "enzyme";

import { SpotifyPlayDirection, PlaybackControls } from "./PlaybackControls";

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
};
describe("PlaybackControls", () => {
  it("renders", () => {
    const wrapper = shallow(<PlaybackControls {...props} />);
    expect(wrapper).toMatchSnapshot();
  });
});
