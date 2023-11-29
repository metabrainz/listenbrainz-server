import * as React from "react";
import { mount } from "enzyme";

import BrainzPlayerUI from "../../src/brainzplayer/BrainzPlayerUI";
import { QueueRepeatModes } from "../../src/brainzplayer/BrainzPlayer";

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
  removeTrackFromQueue: (track: BrainzPlayerQueueItem) => {},
  moveQueueItem: (evt: any) => {},
  setQueue: (queue: BrainzPlayerQueue) => {},
  clearQueue: () => {},
  queue: [],
  queueRepeatMode: QueueRepeatModes.off,
  toggleRepeatMode: () => {},
};
describe("BrainzPlayerUI", () => {
  it("renders", () => {
    const wrapper = mount(<BrainzPlayerUI {...props} />);
    expect(wrapper.find("#brainz-player")).toHaveLength(1);
  });
});
