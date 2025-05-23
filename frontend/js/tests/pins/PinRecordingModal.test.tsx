import * as React from "react";

import { act } from "react-dom/test-utils";
import NiceModal, { NiceModalHocProps } from "@ebay/nice-modal-react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PinRecordingModal, {
  maxBlurbContentLength,
} from "../../src/pins/PinRecordingModal";
import APIServiceClass from "../../src/utils/APIService";
import { GlobalAppContextT } from "../../src/utils/GlobalAppContext";
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";
import {
  renderWithProviders,
  textContentMatcher,
} from "../test-utils/rtl-test-utils";

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

const APIService = new APIServiceClass("");
const globalProps: GlobalAppContextT = {
  APIService,
  websocketsUrl: "",
  currentUser: {
    id: 1,
    name: "name",
    auth_token: "auth_token",
  },
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

jest.unmock("react-toastify");
const user = userEvent.setup();

describe("PinRecordingModal", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });
  it("renders the prompt, input text area, track_name, and artist_name", async () => {
    renderWithProviders(<NiceModal.Provider />, globalProps);
    act(() => {
      NiceModal.show(PinRecordingModal, { ...niceModalProps, recordingToPin });
    });

    await screen.findByRole("dialog");
    await screen.findByText(textContentMatcher("Feel Special by TWICE"));
    // expect(screen.getByText(/Feel Special by TWICE/i)).toBeVisible();
    await screen.findByRole("textbox");
  });

  describe("submitPinRecording", () => {
    it("calls API, and creates a new alert on success", async () => {
      renderWithProviders(<NiceModal.Provider />, globalProps);
      act(() => {
        NiceModal.show(PinRecordingModal, {
          ...niceModalProps,
          recordingToPin,
        });
      });

      const submitButton = await screen.findByRole("button", {
        name: /pin track/i,
      });
      expect(submitButton).not.toBeDisabled();
      await user.click(submitButton);

      expect(submitPinRecordingSpy).toHaveBeenCalledTimes(1);
      expect(submitPinRecordingSpy).toHaveBeenCalledWith(
        "auth_token",
        "recording_msid",
        "recording_mbid",
        undefined
      );
    });

    it("sets default blurbContent in state on success", async () => {
      renderWithProviders(<NiceModal.Provider />, globalProps);
      act(() => {
        NiceModal.show(PinRecordingModal, {
          ...niceModalProps,
          recordingToPin,
        });
      });
      const textInput = await screen.findByRole("textbox");
      await user.type(textInput, "foobar");
      const submitButton = await screen.findByRole("button", {
        name: /pin track/i,
      });
      await user.click(submitButton);

      expect(submitPinRecordingSpy).toHaveBeenCalledWith(
        "auth_token",
        "recording_msid",
        "recording_mbid",
        "foobar"
      );
      expect(textInput).toHaveTextContent("");
    });

    it("does nothing if currentUser.authtoken is not set", async () => {
      renderWithProviders(<NiceModal.Provider />, {
        ...globalProps,
        currentUser: { auth_token: undefined, id: 1, name: "test" }, // auth token not set
      });
      act(() => {
        NiceModal.show(PinRecordingModal, {
          ...niceModalProps,
          recordingToPin,
        });
      });
      const submitButton = await screen.findByRole("button", {
        name: /pin track/i,
      });
      await user.click(submitButton);
      expect(submitPinRecordingSpy).toHaveBeenCalledTimes(0);
    });

    it("calls handleError if error is returned", async () => {
      renderWithProviders(<NiceModal.Provider />, globalProps);
      act(() => {
        NiceModal.show(PinRecordingModal, {
          ...niceModalProps,
          recordingToPin,
        });
      });

      const error = new Error("Beep boop an error occurred");
      submitPinRecordingSpy.mockImplementationOnce(() => {
        throw error;
      });

      const submitButton = await screen.findByRole("button", {
        name: /pin track/i,
      });
      await user.click(submitButton);
      await screen.findByText("Beep boop an error occurred");
    });
  });

  describe("handleBlurbInputChange", () => {
    it("removes line breaks and excessive spaces from input before setting blurbContent in state ", async () => {
      renderWithProviders(<NiceModal.Provider />, globalProps);
      act(() => {
        NiceModal.show(PinRecordingModal, {
          ...niceModalProps,
          recordingToPin,
        });
      });

      const unparsedInput =
        "This string contains \n\n line breaks and multiple   consecutive   spaces.";
      const parsedOutput =
        "This string contains line breaks and multiple consecutive spaces.";

      const textInput = await screen.findByRole("textbox");
      await user.type(textInput, unparsedInput);

      // the string should have been parsed and cleaned up
      expect(textInput).toHaveTextContent(parsedOutput);
    });

    it("does not set blurbContent in state if input length is greater than MAX_BLURB_CONTENT_LENGTH ", async () => {
      renderWithProviders(<NiceModal.Provider />, globalProps);
      act(() => {
        NiceModal.show(PinRecordingModal, {
          ...niceModalProps,
          recordingToPin,
        });
      });
      const textInput = await screen.findByRole("textbox");
      await user.type(textInput, "This string is valid.");

      expect(textInput).toHaveTextContent("This string is valid.");

      const invalidInputString = "a".repeat(maxBlurbContentLength + 1);
      expect(invalidInputString.length).toBeGreaterThan(maxBlurbContentLength);

      await user.type(textInput, invalidInputString);

      // blurbContent should not have changed
      expect(textInput).toHaveTextContent("This string is valid.");
    });
  });
});
