/* eslint-disable jest/no-disabled-tests */

import * as React from "react";
import { mount } from "enzyme";
import * as timeago from "time-ago";
import { GlobalAppContextT } from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";
import BrainzPlayer from "../../src/brainzplayer/BrainzPlayer";

import * as pinsPageProps from "../__mocks__/userPinsProps.json";
import * as APIPins from "../__mocks__/pinProps.json";

import { getListenablePin } from "../../src/utils/utils";

import UserPins from "../../src/pins/UserPins";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

// typescript doesn't recognise string literal values
const props = {
  ...pinsPageProps,
  pins: pinsPageProps.pins as Array<PinnedRecording>,
  newAlert: () => {},
};

const APIPinsPageTwo = {
  count: 1,
  offset: 25,
  pinned_recordings: [
    {
      blurb_content: null,
      created: 1628711647,
      pinned_until: 1628711786,
      recording_mbid: null,
      recording_msid: "a539519f-e99e-4a6a-acc8-b80f6cd38476",
      row_id: 30,
      track_metadata: {
        artist_name: "Lorde",
        track_name: "400 Lux",
      },
    },
  ],
  total_count: 26,
  user_name: "jdaok",
};

// Create a new instance of GlobalAppContext
const mountOptions: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIService("foo"),
    youtubeAuth: pinsPageProps.youtube as YoutubeUser,
    spotifyAuth: pinsPageProps.spotify as SpotifyUser,
    currentUser: pinsPageProps.user,
  },
};

describe("UserPins", () => {
  it("renders correctly on the profile page", () => {
    // Datepicker component uses current time at load as max date,
    // and PinnedRecordingModal component uses current time at load to display recording unpin date,
    // so we have to mock the Date constructor otherwise snapshots will be different every day
    const mockDate = new Date("2021-05-19");
    const fakeDateNow = jest
      .spyOn(global.Date, "now")
      .mockImplementation(() => mockDate.getTime());

    timeago.ago = jest.fn().mockImplementation(() => "1 day ago");
    const wrapper = mount<UserPins>(<UserPins {...props} />, mountOptions);
    expect(wrapper.html()).toMatchSnapshot();
    fakeDateNow.mockRestore();
  });

  it("contains a BrainzPlayer instance", () => {
    const wrapper = mount<UserPins>(<UserPins {...props} />, mountOptions);
    const instance = wrapper.instance();
    expect(wrapper.find(BrainzPlayer)).toHaveLength(1);
  });

  it("renders the correct number of pinned recordings", () => {
    const wrapper = mount<UserPins>(<UserPins {...props} />, mountOptions);

    const ulElement = wrapper.find("#pinned-recordings");
    expect(ulElement).toHaveLength(1);
    expect(ulElement.children()).toHaveLength(props.pins.length);
  });
});

describe("Pagination", () => {
  const pushStateSpy = jest.spyOn(window.history, "pushState");

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe("handleClickOlder", () => {
    it("does nothing if page >= maxPage", async () => {
      const wrapper = mount<UserPins>(<UserPins {...props} />, mountOptions);
      const instance = wrapper.instance();

      const spy = jest.fn().mockImplementation(() => {});
      instance.getPinsFromAPI = spy;
      wrapper.setState({ maxPage: 1 });

      await instance.handleClickOlder();

      expect(wrapper.state("loading")).toBeFalsy();
      expect(spy).not.toHaveBeenCalled();
      expect(pushStateSpy).not.toHaveBeenCalled();
    });

    it("calls the API to get older pins / next page", async () => {
      const wrapper = mount<UserPins>(<UserPins {...props} />, mountOptions);
      const instance = wrapper.instance();

      const apiSpy = jest
        .fn()
        .mockImplementation(() => Promise.resolve(APIPinsPageTwo));
      instance.context.APIService.getPinsForUser = apiSpy;

      const getPinsFromAPISpy = jest.spyOn(instance, "getPinsFromAPI");

      // second page is fetchable
      await instance.handleClickOlder();

      expect(getPinsFromAPISpy).toHaveBeenCalledWith(2);
      expect(apiSpy).toHaveBeenCalledWith(props.user.name, 25, 25);

      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("page")).toEqual(2);
      expect(pushStateSpy).toHaveBeenCalledWith(null, "", `?page=2`);
      expect(wrapper.state("pins")).toEqual(
        APIPinsPageTwo.pinned_recordings as Array<PinnedRecording>
      );
    });
  });

  describe("handleClickNewer", () => {
    it("does nothing if on first page", async () => {
      const wrapper = mount<UserPins>(<UserPins {...props} />, mountOptions);
      const instance = wrapper.instance();

      const spy = jest.fn().mockImplementation(() => {});
      instance.getPinsFromAPI = spy;

      await instance.handleClickNewer();

      expect(wrapper.state("loading")).toBeFalsy();
      expect(spy).not.toHaveBeenCalled();

      wrapper.setState({ page: 2 });
      await instance.handleClickNewer();
      expect(spy).toHaveBeenCalled();
    });

    it("calls the API to get newer pins / previous page", async () => {
      const wrapper = mount<UserPins>(<UserPins {...props} />, mountOptions);
      const instance = wrapper.instance();

      const getPinsFromAPISpy = jest.spyOn(instance, "getPinsFromAPI");

      // move to page 2 before testing fetching page 1
      const apiSpy = jest
        .fn()
        .mockImplementationOnce(() => Promise.resolve(APIPinsPageTwo))
        .mockImplementationOnce(() => Promise.resolve(APIPins));
      instance.context.APIService.getPinsForUser = apiSpy;
      await instance.handleClickOlder();
      await instance.handleClickNewer();

      expect(getPinsFromAPISpy).toHaveBeenCalledWith(2);
      expect(apiSpy).toHaveBeenNthCalledWith(2, props.user.name, 0, 25);

      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("page")).toEqual(1);
      expect(pushStateSpy).toHaveBeenNthCalledWith(2, null, "", `?page=1`);
      expect(wrapper.state("pins")).toEqual(
        APIPins.pinned_recordings as Array<PinnedRecording>
      );
    });
  });
});

describe("removePinFromPinsList", () => {
  it("updates the listens state after removing particular pin", async () => {
    const wrapper = mount<UserPins>(<UserPins {...props} />, mountOptions);
    const instance = wrapper.instance();
    wrapper.setState({ pins: props.pins });

    expect(wrapper.state("pins")).toHaveLength(25);

    const expectedNewFirstPin = props.pins[1];
    instance.removePinFromPinsList(props.pins[0]);

    expect(wrapper.state("pins")).toHaveLength(24);
    expect(wrapper.state("pins")[0].recording_msid).toEqual(
      expectedNewFirstPin.recording_msid
    );
  });
});
