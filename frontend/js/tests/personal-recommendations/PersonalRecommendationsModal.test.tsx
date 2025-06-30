import * as React from "react";
import { screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import NiceModal, { NiceModalHocProps } from "@ebay/nice-modal-react";
import PersonalRecommendationModal, {
  maxBlurbContentLength,
} from "../../src/personal-recommendations/PersonalRecommendationsModal";
import APIServiceClass from "../../src/utils/APIService";
import {
  renderWithProviders,
  textContentMatcher,
} from "../test-utils/rtl-test-utils";

const listenToPersonallyRecommend: Listen = {
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

const testAPIService = new APIServiceClass("");

const niceModalProps: NiceModalHocProps = {
  id: "fnord",
  defaultVisible: true,
};

jest.unmock("react-toastify");

const user = userEvent.setup();

const submitPersonalRecommendationSpy = jest
  .spyOn(testAPIService, "submitPersonalRecommendation")
  .mockImplementation((userToken, userName, metadata) => {
    return Promise.resolve(200);
  });

describe("PersonalRecommendationModal", () => {
  afterEach(() => {
    submitPersonalRecommendationSpy.mockClear();
  });

  it("renders the modal with track details, loads followers", async () => {
    const getFollowersSpy = jest
      .spyOn(testAPIService, "getFollowersOfUser")
      .mockResolvedValue({
        followers: ["bob", "fnord"],
      });
    renderWithProviders(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    act(() => {
      NiceModal.show(PersonalRecommendationModal, {
        ...niceModalProps,
        listenToPersonallyRecommend,
      });
    });

    // A modal is in the document
    await screen.findByRole("dialog");

    // Ensure the component loads the current user's followers
    expect(getFollowersSpy).toHaveBeenCalled();

    screen.getByText(textContentMatcher("Recommend Feel Special"));
  });

  it("calls API, and creates new alert on success", async () => {
    renderWithProviders(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    act(() => {
      NiceModal.show(PersonalRecommendationModal, {
        ...niceModalProps,
        listenToPersonallyRecommend,
      });
    });

    const allButtons = await screen.findAllByRole<HTMLButtonElement>("button");
    const submitButton = allButtons.filter((el) => el.type === "submit").at(0);
    expect(submitButton).toBeDefined();
    // Submit button should be disabled if no recipient is selected
    expect(submitButton).toBeDisabled();

    const usernameTextInput = await screen.findByPlaceholderText(
      "Add followers*"
    );
    await user.type(usernameTextInput, "fnord");

    // Select a recipient
    const userResultButton = await screen.findByRole("menuitem", {
      name: "fnord",
    });
    await user.click(userResultButton);

    // Should be able to click send even without a message
    expect(submitButton).not.toBeDisabled();

    // Add a message anyway for testing
    const messageTextArea = await screen.findByPlaceholderText(
      "You will love this song because..."
    );
    await user.type(messageTextArea, "Hello this is a message");

    // Click submit button
    await user.click(submitButton!);

    expect(submitPersonalRecommendationSpy).toHaveBeenCalledTimes(1);
    expect(submitPersonalRecommendationSpy).toHaveBeenCalledWith(
      "never_gonna",
      "FNORD",
      {
        recording_mbid: "recording_mbid",
        recording_msid: "recording_msid",
        blurb_content: "Hello this is a message",
        users: ["fnord"],
      }
    );
    screen.getByText(
      textContentMatcher("You recommended this track to 1 user")
    );
    screen.getByText(
      textContentMatcher("You recommended this track to 1 user")
    );
  });

  it("does nothing if userToken not set", async () => {
    renderWithProviders(<NiceModal.Provider />, {
      APIService: testAPIService,
      currentUser: { auth_token: undefined, id: 1, name: "test" },
    });
    act(() => {
      NiceModal.show(PersonalRecommendationModal, {
        ...niceModalProps,
        listenToPersonallyRecommend,
      });
    });
    const submitButton = await screen.findByText(/Send Recommendation/i);
    expect(submitButton).toBeDisabled();

    // Select a recipient
    const usernameTextInput = await screen.findByPlaceholderText(
      "Add followers*"
    );
    await user.type(usernameTextInput, "fnord");
    const userResultButton = await screen.findByRole("menuitem", {
      name: "fnord",
    });
    await user.click(userResultButton);

    expect(submitButton).not.toBeDisabled();
    await user.click(submitButton);

    expect(submitPersonalRecommendationSpy).not.toHaveBeenCalled();
  });

  it("Shows an error message in case of error", async () => {
    const error = new Error("error");
    submitPersonalRecommendationSpy.mockRejectedValueOnce(error);
    renderWithProviders(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    act(() => {
      NiceModal.show(PersonalRecommendationModal, {
        ...niceModalProps,
        listenToPersonallyRecommend,
      });
    });

    // Select a recipient
    const usernameTextInput = await screen.findByPlaceholderText(
      "Add followers*"
    );
    await user.type(usernameTextInput, "fnord");
    const userResultButton = await screen.findByRole("menuitem", {
      name: "fnord",
    });
    await user.click(userResultButton);

    const submitButton = await screen.findByText(/Send Recommendation/i);
    await user.click(submitButton);

    await screen.findByText("Error while recommending a track");
  });

  describe("handleBlurbInputChange", () => {
    it("removes line breaks and excessive spaces from input before setting blurbContent in state ", async () => {
      renderWithProviders(<NiceModal.Provider />, {
        APIService: testAPIService,
      });
      act(() => {
        NiceModal.show(PersonalRecommendationModal, {
          ...niceModalProps,
          listenToPersonallyRecommend,
        });
      });

      const unparsedInput =
        "This string contains \n\n line breaks and multiple   consecutive   spaces.";

      // Select a recipient
      const usernameTextInput = await screen.findByPlaceholderText(
        "Add followers*"
      );
      await user.type(usernameTextInput, "fnord");
      const userResultButton = await screen.findByRole("menuitem", {
        name: "fnord",
      });
      await user.click(userResultButton);

      // simulate writing in the textArea
      const messageTextArea = await screen.findByPlaceholderText(
        "You will love this song because..."
      );
      await user.type(messageTextArea, unparsedInput);

      const submitButton = await screen.findByText(/Send Recommendation/i);
      await user.click(submitButton);

      // the string should have been parsed and cleaned up
      expect(submitPersonalRecommendationSpy).toHaveBeenCalledWith(
        "never_gonna",
        "FNORD",
        {
          recording_mbid: "recording_mbid",
          recording_msid: "recording_msid",
          blurb_content:
            "This string contains line breaks and multiple consecutive spaces.",
          users: ["fnord"],
        }
      );
    });

    it("does not set blurbContent in state if input length is greater than MAX_BLURB_CONTENT_LENGTH ", async () => {
      renderWithProviders(<NiceModal.Provider />, {
        APIService: testAPIService,
      });
      act(() => {
        NiceModal.show(PersonalRecommendationModal, {
          ...niceModalProps,
          listenToPersonallyRecommend,
        });
      });

      // Select a recipient
      const usernameTextInput = await screen.findByPlaceholderText(
        "Add followers*"
      );
      await user.type(usernameTextInput, "fnord");
      const userResultButton = await screen.findByRole("menuitem", {
        name: "fnord",
      });
      await user.click(userResultButton);

      const messageTextArea = await screen.findByPlaceholderText<
        HTMLTextAreaElement
      >("You will love this song because...");

      // simulate pasting  text content in the textArea
      await user.click(messageTextArea);
      await user.paste("This string is valid.");
      expect(messageTextArea.value).toEqual("This string is valid.");

      const invalidInputString = "a".repeat(maxBlurbContentLength + 1);
      expect(invalidInputString.length).toBeGreaterThan(maxBlurbContentLength);
      await user.click(messageTextArea);
      await user.paste(invalidInputString);

      // blurbContent should not have changed
      expect(messageTextArea.value).toEqual("This string is valid.");
    });
  });
});
