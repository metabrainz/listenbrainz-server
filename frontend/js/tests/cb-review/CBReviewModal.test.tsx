import * as React from "react";
import NiceModal from "@ebay/nice-modal-react";
import userEvent from "@testing-library/user-event";
import { merge } from "lodash";
import * as lookupMBRelease from "../__mocks__/lookupMBRelease.json";
import * as lookupMBReleaseFromTrack from "../__mocks__/lookupMBReleaseFromTrack.json";

import CBReviewModal, {
  CBReviewModalProps,
} from "../../src/cb-review/CBReviewModal";
import { act, render, screen } from "../test-utils/rtl-test-utils";

import APIService from "../../src/utils/APIService";

jest.unmock("react-toastify");

const listen: Listen = {
  track_metadata: {
    artist_name: "Britney Spears",
    release_name: "The Essential Britney Spears",
    additional_info: {
      recording_mbid: "2bf47421-2344-4255-a525-e7d7f54de742",
      listening_from: "lastfm",
      recording_msid: "ff32f7c7-c8ce-4048-b392-770e013bc05b",
      artist_mbids: ["45a663b5-b1cb-4a91-bff6-2bef7bbfdd76"],
    },
    track_name: "Criminal",
  },
  listened_at: 1628634357,
  listened_at_iso: "2021-08-10T22:25:57Z",
};

const props: CBReviewModalProps = {
  listen,
};

const testAPIService = new APIService("FOO");
const submitReviewToCBSpy = jest
  .spyOn(testAPIService, "submitReviewToCB")
  .mockResolvedValue({
    metadata: { review_id: "new-review-id-that-API-returns" },
  });

const lookupMBReleaseFromTrackSpy = jest
  .spyOn(testAPIService, "lookupMBReleaseFromTrack")
  .mockResolvedValue(lookupMBReleaseFromTrack);

const lookupMBReleaseSpy = jest
  .spyOn(testAPIService, "lookupMBRelease")
  .mockResolvedValue(lookupMBRelease);

// mock api refreshtoken sending a new token
const apiRefreshSpy = jest
  .spyOn(testAPIService, "refreshAccessToken")
  .mockResolvedValue("this is new token");

describe("CBReviewModal", () => {
  const user = userEvent.setup();
  userEvent.setup();

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the modal correctly", async () => {
    render(<NiceModal.Provider />);
    await act(async () => {
      NiceModal.show(CBReviewModal, { ...props });
    });
    expect(screen.getByRole("dialog")).toBeVisible();
  });

  it("requires the user to be logged in, showing a message otherwise", async () => {
    render(<NiceModal.Provider />, { critiquebrainzAuth: {} });
    await act(async () => {
      NiceModal.show(CBReviewModal, { ...props });
    });

    expect(
      screen.getByText(/connect to your critiquebrainz account/i)
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: /connect to critiquebrainz/i })
    ).toBeVisible();
  });
  it("prevents submission if license was not accepted", async () => {
    const { getByRole } = render(<NiceModal.Provider />);
    await act(async () => {
      NiceModal.show(CBReviewModal, { ...props });
    });
    const textInput = getByRole("textbox");
    const checkbox = getByRole("checkbox");
    await user.type(
      textInput,
      "This review text is more than 25 characters..."
    );
    // Make sure the validation message is not visible and we have sufficient length
    const textTooShortMessage = screen.queryByText(
      /your review needs to be longer than/i
    );
    expect(textTooShortMessage).toBeNull();

    expect(checkbox).not.toBeChecked();
    const submitButton = getByRole("button", { name: /submit review/i });
    expect(submitButton).toBeDisabled();
    // Try to click anyway
    await user.click(submitButton);

    expect(submitReviewToCBSpy).not.toHaveBeenCalled();
  });

  it("submits the review and displays a success alert", async () => {
    const { getByRole } = render(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    await act(async () => {
      NiceModal.show(CBReviewModal, { ...props });
    });

    const textInput = getByRole("textbox");
    const checkbox = getByRole("checkbox");
    await user.type(
      textInput,
      "This review text is more than 25 characters..."
    );
    await user.click(checkbox);

    expect(getByRole("textbox")).toHaveTextContent(
      "This review text is more than 25 characters..."
    );
    expect(checkbox).toBeChecked();

    const submitButton = getByRole("button", { name: /submit review/i });
    expect(submitButton).toBeEnabled();
    await user.click(submitButton);

    expect(submitReviewToCBSpy).toHaveBeenCalledWith("FNORD", "never_gonna", {
      entity_name: "Criminal",
      entity_id: "2bf47421-2344-4255-a525-e7d7f54de742",
      entity_type: "recording",
      languageCode: "en",
      rating: undefined,
      text: "This review text is more than 25 characters...",
    });

    // expect a success toast message
    await screen.findByText("Your review was submitted to CritiqueBrainz!");
  });

  it("catches API call errors and displays it on screen", async () => {
    submitReviewToCBSpy.mockRejectedValueOnce({
      message: "Computer says no!",
    });

    const { getByRole, findByText } = render(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    await act(async () => {
      NiceModal.show(CBReviewModal, { ...props });
    });

    const checkbox = getByRole("checkbox");
    const textInput = getByRole("textbox");
    const submitButton = getByRole("button", { name: /submit review/i });

    /** We shouldn't need a call to `act` here, but for some reason
     * the test doesn't pass if I don't wrap these user interactions in it.
     * Perhaps some concurrency reasons?
     * In any case, this results in the following warning in the console:
     * `Warning: The current testing environment is not configured to support act(...)`
     */
    await act(async () => {
      await user.click(checkbox);
      await user.type(
        textInput,
        "This review text is more than 25 characters..."
      );
      await user.click(submitButton);
    });

    expect(submitReviewToCBSpy).toHaveBeenCalled();
    // expect error toast with title "Your review was submitted to CritiqueBrainz"
    await findByText("Error while submitting review to CritiqueBrainz");
  });

  it("shows a message if text content is too short and prevents submission", async () => {
    const { getByRole } = render(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    await act(async () => {
      NiceModal.show(CBReviewModal, { ...props });
    });
    const checkbox = getByRole("checkbox");
    const textInput = getByRole("textbox");
    const submitButton = getByRole("button", { name: /submit review/i });
    await user.click(checkbox);
    await user.type(textInput, "Too short!");
    // Submit button should be disabled
    expect(submitButton).toBeDisabled();
    // Try to click anyway
    await user.click(submitButton);

    expect(submitReviewToCBSpy).not.toHaveBeenCalled();
    // expect a visible validation message
    await screen.findByText(/your review needs to be longer than/i);
  });

  it("prevents submission if there is no entity to review", async () => {
    const { queryByRole } = render(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    await act(async () => {
      NiceModal.show(CBReviewModal, {
        listen: {
          listened_at: 0,
          track_metadata: { artist_name: "Bob", track_name: "FNORD" },
        },
      });
    });
    const checkbox = queryByRole("checkbox");
    const textInput = queryByRole("textbox");
    const submitButton = queryByRole("button", { name: /submit review/i });

    expect(textInput).toBeNull();
    expect(checkbox).toBeNull();
    expect(submitButton).toBeNull();

    // Make sure the validation message is not visible and we have sufficient length
    const textTooShortMessage = screen.queryByText(
      /your review needs to be longer than/i
    );
    expect(textTooShortMessage).toBeNull();

    // expect a visible validation message
    await screen.findByText(/We could not link/i);
  });

  it("getGroupMBIDFromRelease calls API and returns the correct release group MBID", async () => {
    const releaseMBID = "40ef0ae1-5626-43eb-838f-1b34187519bf";
    const { getByRole } = render(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    await act(async () => {
      NiceModal.show(CBReviewModal, {
        listen: merge({}, listen, {
          track_metadata: {
            additional_info: {
              release_group_mbid: null,
              release_mbid: releaseMBID,
            },
          },
        }),
      });
    });

    expect(lookupMBReleaseSpy).toHaveBeenCalledTimes(1);
    expect(lookupMBReleaseSpy).toHaveBeenCalledWith(releaseMBID);

    const RGSelectButton = getByRole("button", {
      name: "The Essential Britney Spears (release group)",
    });
    expect(RGSelectButton).toBeVisible();
  });
  it("getRecordingMBIDFromTrack calls API and returns the correct recording MBID", async () => {
    const mbid = "0255f1ea-3199-49b4-8b5c-bdcc3716ebc9";
    const { getAllByRole } = render(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    await act(async () => {
      NiceModal.show(CBReviewModal, {
        listen: merge({}, listen, {
          track_metadata: {
            additional_info: {
              track_mbid: mbid,
              recording_mbid: null,
            },
          },
        }),
      });
    });

    expect(lookupMBReleaseFromTrackSpy).toHaveBeenCalledTimes(1);
    expect(lookupMBReleaseFromTrackSpy).toHaveBeenCalledWith(mbid);

    const selectRecordingButton = getAllByRole("button", {
      name: "Criminal (recording)",
    });
    expect(selectRecordingButton).toHaveLength(2);
  });
  it("retries once if API throws invalid token error", async () => {
    submitReviewToCBSpy.mockRejectedValueOnce({ message: "invalid_token" });

    const { getByRole } = render(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    await act(async () => {
      NiceModal.show(CBReviewModal, { ...props });
    });

    const textInput = getByRole("textbox");
    const checkbox = getByRole("checkbox");
    await user.click(checkbox);
    expect(checkbox).toBeChecked();
    await user.type(
      textInput,
      "This review text is more than 25 characters..."
    );
    const submitButton = getByRole("button", { name: /submit review/i });
    expect(submitButton).toBeEnabled();

    await user.click(submitButton);

    expect(apiRefreshSpy).toHaveBeenCalledTimes(1); // a new token is requested once
    expect(apiRefreshSpy).toHaveBeenCalledWith("critiquebrainz");

    // new token was received, and the submission retried
    expect(submitReviewToCBSpy).toHaveBeenCalledTimes(2);

    // expect a success toast message
    await screen.findByText("Your review was submitted to CritiqueBrainz!");
  });
});
