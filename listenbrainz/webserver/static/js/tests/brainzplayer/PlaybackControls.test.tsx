import * as React from "react";
import { mount } from "enzyme";

import PlaybackControls from "../../src/brainzplayer/PlaybackControls";

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
  currentFeedback: 0 as ListenFeedBack,
  submitFeedback: (score: ListenFeedBack): any => {},
};
describe("PlaybackControls", () => {
  it("renders", () => {
    const wrapper = mount(<PlaybackControls {...props} />);
    expect(wrapper).toMatchSnapshot();
  });
});
