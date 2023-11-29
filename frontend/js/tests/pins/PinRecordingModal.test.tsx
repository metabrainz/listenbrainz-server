import * as React from "react";
import { mount, ReactWrapper } from "enzyme";

import { act } from "react-dom/test-utils";
import NiceModal, { NiceModalHocProps } from "@ebay/nice-modal-react";
import PinRecordingModal, {
  maxBlurbContentLength,
} from "../../src/pins/PinRecordingModal";
import APIServiceClass from "../../src/utils/APIService";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import { waitForComponentToPaint } from "../test-utils";
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";

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
const APIService = new APIServiceClass("");
const globalProps: GlobalAppContextT = {
  APIService,
  websocketsUrl: "",
  currentUser: user,
  spotifyAuth: {},
  youtubeAuth: {},
  recordingFeedbackManager: new RecordingFeedbackManager(APIService, {
    name: "Fnord",
  }),
};

const niceModalProps: NiceModalHocProps = {
  id: "fnord",
  defaultVisible: true,
};

const submitPinRecordingSpy = jest
  .spyOn(APIService, "submitPinRecording")
  .mockImplementation(() =>
    Promise.resolve({ status: "ok", data: pinnedRecordingFromAPI })
  );

describe("PinRecordingModal", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });
  it("renders the prompt, input text area, track_name, and artist_name", () => {
    const wrapper = mount(
      <GlobalAppContext.Provider value={globalProps}>
        <NiceModal.Provider>
          <PinRecordingModal
            {...niceModalProps}
            recordingToPin={recordingToPin}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    );
    const modalElement = wrapper.find("#PinRecordingModal");
    expect(modalElement).toHaveLength(1);
    expect(modalElement.getDOMNode()).toHaveTextContent("Feel Special");
    expect(modalElement.getDOMNode()).toHaveTextContent("TWICE");
    expect(modalElement.find("textarea")).toHaveLength(1);
  });

  describe("submitPinRecording", () => {
    it("calls API, and creates a new alert on success", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <PinRecordingModal
              {...niceModalProps}
              recordingToPin={recordingToPin}
            />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );

      await act(async () => {
        const submitButton = wrapper.find("button[type='submit']").first();
        submitButton?.simulate("click");
      });
      await waitForComponentToPaint(wrapper);

      expect(submitPinRecordingSpy).toHaveBeenCalledTimes(1);
      expect(submitPinRecordingSpy).toHaveBeenCalledWith(
        "auth_token",
        "recording_msid",
        "recording_mbid",
        undefined
      );
    });

    it("sets default blurbContent in state on success", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <PinRecordingModal
              {...niceModalProps}
              recordingToPin={recordingToPin}
            />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );
      await act(async () => {
        const blurbTextArea = wrapper
          .find("textarea[name='blurb-content']")
          .first();
        blurbTextArea.simulate("change", { target: { value: "foobar" } });
      });
      await act(async () => {
        const submitButton = wrapper.find("button[type='submit']").first();
        submitButton?.simulate("click");
      });
      await waitForComponentToPaint(wrapper);
      expect(submitPinRecordingSpy).toHaveBeenCalledWith(
        "auth_token",
        "recording_msid",
        "recording_mbid",
        "foobar"
      );
      expect(
        wrapper.find("textarea[name='blurb-content']").first().props().value
      ).toEqual("");
    });

    it("does nothing if currentUser.authtoken is not set", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            currentUser: { auth_token: undefined, id: 1, name: "test" }, // auth token not set
          }}
        >
          <NiceModal.Provider>
            <PinRecordingModal
              {...niceModalProps}
              recordingToPin={recordingToPin}
            />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      await act(async () => {
        const submitButton = wrapper.find("button[type='submit']").first();
        submitButton?.simulate("click");
      });
      await waitForComponentToPaint(wrapper);
      expect(submitPinRecordingSpy).toHaveBeenCalledTimes(0);
    });

    it("calls handleError if error is returned", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <PinRecordingModal
              {...niceModalProps}
              recordingToPin={recordingToPin}
            />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );

      const error = new Error("error");
      submitPinRecordingSpy.mockImplementationOnce(() => {
        throw error;
      });

      await act(async () => {
        const submitButton = wrapper.find("button[type='submit']").first();
        submitButton?.simulate("click");
      });
      await waitForComponentToPaint(wrapper);
    });
  });

  describe("handleBlurbInputChange", () => {
    it("removes line breaks and excessive spaces from input before setting blurbContent in state ", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <PinRecordingModal
              {...niceModalProps}
              recordingToPin={recordingToPin}
            />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );
      await waitForComponentToPaint(wrapper);

      const unparsedInput =
        "This string contains \n\n line breaks and multiple   consecutive   spaces.";

      // simulate writing in the textArea
      await act(() => {
        wrapper
          .find("#blurb-content")
          .first()
          .simulate("change", {
            target: { value: unparsedInput },
          });
      });
      await waitForComponentToPaint(wrapper);

      // the string should have been parsed and cleaned up
      const blurbTextArea = wrapper
        .find("textarea[name='blurb-content']")
        .first();
      expect(blurbTextArea.props().value).toEqual(
        "This string contains line breaks and multiple consecutive spaces."
      );
    });

    it("does not set blurbContent in state if input length is greater than MAX_BLURB_CONTENT_LENGTH ", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <PinRecordingModal
              {...niceModalProps}
              recordingToPin={recordingToPin}
            />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );
      await act(async () => {
        wrapper
          .find("textarea[name='blurb-content']")
          .first()
          .simulate("change", {
            target: { value: "This string is valid." },
          });
      });
      await waitForComponentToPaint(wrapper);

      const blurbTextArea = wrapper
        .find("textarea[name='blurb-content']")
        .first();
      expect(blurbTextArea.props().value).toEqual("This string is valid.");

      const invalidInputString = "a".repeat(maxBlurbContentLength + 1);
      expect(invalidInputString.length).toBeGreaterThan(maxBlurbContentLength);

      await act(async () => {
        wrapper
          .find("textarea[name='blurb-content']")
          .first()
          .simulate("change", {
            target: { value: invalidInputString },
          });
      });
      await waitForComponentToPaint(wrapper);

      // blurbContent should not have changed
      expect(blurbTextArea.props().value).toEqual("This string is valid.");
    });
  });
});
