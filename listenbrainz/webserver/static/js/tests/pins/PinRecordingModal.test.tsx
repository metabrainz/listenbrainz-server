import * as React from "react";
import { mount, ReactWrapper } from "enzyme";

import { act } from "react-dom/test-utils";
import PinRecordingModal, {
  PinRecordingModalProps,
  PinRecordingModalState,
} from "../../src/pins/PinRecordingModal";
import APIServiceClass from "../../src/utils/APIService";
import GlobalAppContext from "../../src/utils/GlobalAppContext";
import { waitForComponentToPaint } from "../test-utils";

const recordingToPin: Listen = {
  listened_at: 1605927742,
  track_metadata: {
    artist_name: "TWICE",
    track_name: "Feel Special",
    additional_info: {
      release_mbid: "release_mbid",
      recording_msid: "recording_msid",
      recording_mbid: "recording_mbid",
    },
  },
};

const pinnedRecordingFromAPI: PinnedRecording = {
  created: 1605927742,
  pinned_until: 1605927893,
  blurb_content:
    "Our perception of the passing of time is really just a side-effect of gravity",
  recording_mbid: "recording_mbid",
  row_id: 1,
  track_metadata: {
    artist_name: "TWICE",
    track_name: "Feel Special",
    additional_info: {
      release_mbid: "release_mbid",
      recording_msid: "recording_msid",
      recording_mbid: "recording_mbid",
    },
  },
};

const user = {
  id: 1,
  name: "name",
  auth_token: "auth_token",
};

const globalProps = {
  APIService: new APIServiceClass(""),
  currentUser: user,
  spotifyAuth: {},
  youtubeAuth: {},
};

describe("PinRecordingModal", () => {
  let wrapper:
    | ReactWrapper<
        PinRecordingModalProps,
        PinRecordingModalState,
        PinRecordingModal
      >
    | undefined;
  beforeEach(() => {
    wrapper = undefined;
  });
  afterEach(() => {
    if (wrapper) {
      /* Unmount the wrapper at the end of each test, otherwise react-dom throws errors
        related to async lifecycle methods run against a missing dom 'document'.
        See https://github.com/facebook/react/issues/15691
      */
      wrapper.unmount();
    }
  });
  it("renders the prompt, input text area, track_name, and artist_name", () => {
    // This component uses current time at load to display,
    // so we have to mock the Date constructor - otherwise, snapshots will be different every day
    const mockDate = new Date("2021-01-01");
    const fakeDateNow = jest
      .spyOn(global.Date, "now")
      .mockImplementation(() => mockDate.getTime());

    wrapper = mount<PinRecordingModal>(
      <PinRecordingModal recordingToPin={recordingToPin} newAlert={jest.fn()} />
    );
    expect(wrapper.html()).toMatchSnapshot();
    fakeDateNow.mockRestore();
  });

  describe("submitPinRecording", () => {
    it("calls API, and creates a new alert on success", async () => {
      wrapper = mount<PinRecordingModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <PinRecordingModal
            recordingToPin={recordingToPin}
            newAlert={jest.fn()}
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const spy = jest.spyOn(instance.context.APIService, "submitPinRecording");
      spy.mockImplementation(() =>
        Promise.resolve({ status: "ok", data: pinnedRecordingFromAPI })
      );

      await instance.submitPinRecording();
      await waitForComponentToPaint(wrapper);

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith(
        "auth_token",
        "recording_msid",
        "recording_mbid",
        undefined
      );
      expect(instance.props.newAlert).toHaveBeenCalledTimes(1);
    });

    it("sets default blurbContent in state on success", async () => {
      wrapper = mount<PinRecordingModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <PinRecordingModal
            recordingToPin={recordingToPin}
            newAlert={jest.fn()}
          />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();
      instance.context.APIService.submitPinRecording = jest
        .fn()
        .mockImplementation(() =>
          Promise.resolve({ status: "ok", data: pinnedRecordingFromAPI })
        );
      await act(() => {
        wrapper!.setState({ blurbContent: "foobar" }); // submit with this blurbContent
      });

      // submitPinRecording and check that blurbContent was reset
      const setStateSpy = jest.spyOn(instance, "setState");
      await instance.submitPinRecording();
      await waitForComponentToPaint(wrapper);

      expect(setStateSpy).toHaveBeenCalledTimes(1);
      expect(wrapper.state("blurbContent")).toEqual("");
    });

    it("does nothing if CurrentUser.authtoken is not set", async () => {
      wrapper = mount<PinRecordingModal>(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            currentUser: { auth_token: undefined, id: 1, name: "test" }, // auth token not set
          }}
        >
          <PinRecordingModal
            recordingToPin={recordingToPin}
            newAlert={jest.fn()}
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const spy = jest.spyOn(instance.context.APIService, "submitPinRecording");
      spy.mockImplementation(() =>
        Promise.resolve({ status: "ok", data: pinnedRecordingFromAPI })
      );

      await instance.submitPinRecording();
      await waitForComponentToPaint(wrapper);
      expect(spy).toHaveBeenCalledTimes(0);
    });

    it("calls handleError if error is returned", async () => {
      wrapper = mount<PinRecordingModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <PinRecordingModal
            recordingToPin={recordingToPin}
            newAlert={jest.fn()}
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      instance.handleError = jest.fn();

      const error = new Error("error");
      const spy = jest.spyOn(instance.context.APIService, "submitPinRecording");
      spy.mockImplementation(() => {
        throw error;
      });

      instance.submitPinRecording();
      await waitForComponentToPaint(wrapper);
      expect(instance.handleError).toHaveBeenCalledTimes(1);
      expect(instance.handleError).toHaveBeenCalledWith(
        error,
        "Error while pinning recording"
      );
    });
  });

  describe("handleBlurbInputChange", () => {
    it("removes line breaks and excessive spaces from input before setting blurbContent in state ", async () => {
      wrapper = mount<PinRecordingModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <PinRecordingModal
            recordingToPin={recordingToPin}
            newAlert={jest.fn()}
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const unparsedInput =
        "This string contains \n\n line breaks and multiple   consecutive   spaces.";
      const setStateSpy = jest.spyOn(instance, "setState");

      // simulate writing in the textArea
      const blurbContentInput = wrapper.find("#blurb-content").first();
      await act(() => {
        blurbContentInput.simulate("change", {
          target: { value: unparsedInput },
        });
      });

      // the string should have been parsed and cleaned up
      expect(wrapper.state("blurbContent")).toEqual(
        "This string contains line breaks and multiple consecutive spaces."
      );
      expect(setStateSpy).toHaveBeenCalledTimes(1);
    });

    it("does not set blurbContent in state if input length is greater than MAX_BLURB_CONTENT_LENGTH ", async () => {
      wrapper = mount<PinRecordingModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <PinRecordingModal
            recordingToPin={recordingToPin}
            newAlert={jest.fn()}
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      // simulate writing in the textArea
      const blurbContentInput = wrapper.find("#blurb-content").first();
      await act(() => {
        blurbContentInput.simulate("change", {
          target: { value: "This string is valid." },
        });
      });

      const invalidInputLength = "a".repeat(instance.maxBlurbContentLength + 1);
      expect(invalidInputLength.length).toBeGreaterThan(
        instance.maxBlurbContentLength
      );

      const setStateSpy = jest.spyOn(instance, "setState");

      await act(() => {
        blurbContentInput.simulate("change", {
          target: { value: invalidInputLength },
        });
      });

      // blurbContent should not have changed
      expect(setStateSpy).not.toHaveBeenCalled();
      expect(wrapper.state("blurbContent")).toEqual("This string is valid.");
    });
  });

  describe("handleError", () => {
    it("calls newAlert", async () => {
      wrapper = mount<PinRecordingModal>(
        <PinRecordingModal
          recordingToPin={recordingToPin}
          newAlert={jest.fn()}
        />
      );
      const instance = wrapper.instance();

      instance.handleError("error");
      expect(instance.props.newAlert).toHaveBeenCalledWith(
        "danger",
        "Error",
        "error"
      );
    });
  });
});
