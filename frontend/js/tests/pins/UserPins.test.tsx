/* eslint-disable jest/no-disabled-tests */

import * as React from "react";
import { mount, ReactWrapper } from "enzyme";
import * as timeago from "time-ago";
import { act } from "react-dom/test-utils";
import { GlobalAppContextT } from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";

import * as pinsPageProps from "../__mocks__/userPinsProps.json";
import * as APIPins from "../__mocks__/pinProps.json";

import UserPins, {
  UserPinsProps,
  UserPinsState,
} from "../../src/user/taste/components/UserPins";
import PinnedRecordingCard from "../../src/user/components/PinnedRecordingCard";
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";
import { ReactQueryWrapper } from "../test-react-query";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

function UserPinsWithWrapper(props: UserPinsProps) {
  return (
    <ReactQueryWrapper>
      <UserPins {...props} />
    </ReactQueryWrapper>
  );
}

// typescript doesn't recognise string literal values
const props = {
  ...pinsPageProps,
  pins: pinsPageProps.pins as Array<PinnedRecording>,
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
    websocketsUrl: "",
    youtubeAuth: pinsPageProps.youtube as YoutubeUser,
    spotifyAuth: pinsPageProps.spotify as SpotifyUser,
    currentUser: pinsPageProps.user,
    recordingFeedbackManager: new RecordingFeedbackManager(
      new APIService("foo"),
      { name: "Fnord" }
    ),
  },
};

describe("UserPins", () => {
  it("renders correctly", () => {
    const wrapper = mount(<UserPinsWithWrapper {...props} />, mountOptions);
    expect(wrapper.find("#pinned-recordings")).toHaveLength(1);
    expect(wrapper.getDOMNode()).toHaveTextContent("Lorde");
    expect(wrapper.getDOMNode()).toHaveTextContent("400 Lux");
  });

  it("renders the correct number of pinned recordings", () => {
    const wrapper = mount(<UserPinsWithWrapper {...props} />, mountOptions);

    const wrapperElement = wrapper.find("#pinned-recordings");
    const pinnedRecordings = wrapperElement.find(PinnedRecordingCard);
    expect(pinnedRecordings).toHaveLength(props.pins.length);
  });

  describe("handleLoadMore", () => {
    describe("handleClickOlder", () => {
      it("does nothing if page >= maxPage", async () => {
        const wrapper = mount(<UserPinsWithWrapper {...props} />, mountOptions);
        const userPinWrapper = wrapper.find(UserPins);
        const instance = userPinWrapper.instance() as UserPins;

        const spy = jest.fn().mockImplementation(() => {});
        instance.getPinsFromAPI = spy;
        await act(() => {
          userPinWrapper.setState({ maxPage: 1 });
        });

        await act(async () => {
          await instance.handleLoadMore();
        });

        expect(userPinWrapper.state("loading")).toBeFalsy();
        expect(spy).not.toHaveBeenCalled();
      });

      it("calls the API to get next page", async () => {
        const wrapper = mount(<UserPinsWithWrapper {...props} />, mountOptions);
        const userPinWrapper = wrapper.find(UserPins);
        const instance = userPinWrapper.instance() as UserPins;

        const apiSpy = jest
          .fn()
          .mockImplementation(() => Promise.resolve(APIPinsPageTwo));
        instance.context.APIService.getPinsForUser = apiSpy;

        const getPinsFromAPISpy = jest.spyOn(instance, "getPinsFromAPI");

        // second page is fetchable
        await act(async () => {
          await instance.handleLoadMore();
        });

        expect(getPinsFromAPISpy).toHaveBeenCalledWith(2);
        expect(apiSpy).toHaveBeenCalledWith(props.user.name, 25, 25);

        expect(userPinWrapper.state("loading")).toBeFalsy();
        expect(userPinWrapper.state("page")).toEqual(2);
        // result should be combined previous pins and new pins
        expect(userPinWrapper.state("pins")).toEqual([
          ...props.pins,
          ...APIPinsPageTwo.pinned_recordings,
        ]);
      });
    });
  });

  describe("removePinFromPinsList", () => {
    it("updates the listens state after removing particular pin", async () => {
      const wrapper = mount(<UserPinsWithWrapper {...props} />, mountOptions);
      const userPinWrapper = wrapper.find(UserPins);
      const instance = userPinWrapper.instance() as UserPins;

      await act(() => {
        userPinWrapper.setState({ pins: props.pins });
      });

      expect(userPinWrapper.state("pins")).toHaveLength(25);

      const expectedNewFirstPin = props.pins[1];
      await act(() => {
        instance.removePinFromPinsList(props.pins[0]);
      });

      expect(userPinWrapper.state("pins")).toHaveLength(24);
      expect(userPinWrapper.state("pins")[0].recording_msid).toEqual(
        expectedNewFirstPin.recording_msid
      );
    });
  });
});
