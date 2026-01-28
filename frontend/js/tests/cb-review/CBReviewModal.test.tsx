import * as React from "react";
import NiceModal from "@ebay/nice-modal-react";
import userEvent from "@testing-library/user-event";
import { merge } from "lodash";
import { act, waitFor, screen, cleanup } from "@testing-library/react";
import * as lookupMBRelease from "../__mocks__/lookupMBRelease.json";
import * as lookupMBReleaseFromTrack from "../__mocks__/lookupMBReleaseFromTrack.json";

import CBReviewModal, {
  CBReviewModalProps,
} from "../../src/cb-review/CBReviewModal";
import { renderWithProviders } from "../test-utils/rtl-test-utils";

import APIService from "../../src/utils/APIService";

jest.unmock("react-toastify");
jest.mock("@cospired/i18n-iso-languages", () => {
  return {
    registerLocale: jest.fn(),
    getNames: () => {
      return ["English", "Lojban", "Klingon"];
    },
  };
});

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

const user = userEvent.setup();

describe("CBReviewModal", () => {
  jest.setTimeout(10000);
  afterEach(() => {
    cleanup();
    jest.clearAllMocks();
  });

  it("renders the modal correctly", async () => {
    renderWithProviders(<NiceModal.Provider />);
    act(() => {
      NiceModal.show(CBReviewModal, { ...props });
    });

    await screen.findByRole("dialog");
  });

  it("requires the user to be logged in, showing a message otherwise", async () => {
    renderWithProviders(<NiceModal.Provider />, { critiquebrainzAuth: {} });
    act(() => {
      NiceModal.show(CBReviewModal, { ...props });
    });

    expect(
      screen.getByText(/connect to your critiquebrainz account/i)
    ).toBeVisible();
    await screen.findByRole("button", { name: /connect to critiquebrainz/i });
  });

  it("prevents submission if license was not accepted", async () => {
    renderWithProviders(<NiceModal.Provider />);
    act(() => {
      NiceModal.show(CBReviewModal, { ...props });
    });
    const textInput = await screen.findByRole("textbox");
    const checkbox = await screen.findByRole("checkbox");
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
    const submitButton = await screen.findByRole("button", {
      name: /submit review/i,
    });
    expect(submitButton).toBeDisabled();
    // Try to click anyway
    await user.click(submitButton);

    await waitFor(() => expect(submitReviewToCBSpy).not.toHaveBeenCalled());
  });

  it("submits the review and displays a success alert", async () => {
    // The modal closes upon successful submission, which messes up the following test
    // Isolate this modal from other tests
    const apiService = new APIService("FOO");
    const submitReviewSpy = jest
      .spyOn(apiService, "submitReviewToCB")
      .mockResolvedValue({
        metadata: { review_id: "new-review-id-that-API-returns" },
      });

    NiceModal.register("cb-modal-1", CBReviewModal);
    renderWithProviders(<NiceModal.Provider />, {
      APIService: apiService,
    });
    act(() => {
      NiceModal.show("cb-modal-1", { ...props });
    });

    const textInput = await screen.findByRole("textbox");
    const checkbox = await screen.findByRole("checkbox");
    await user.type(
      textInput,
      "This review text is more than 25 characters..."
    );
    await user.click(checkbox);

    expect(textInput).toHaveTextContent(
      "This review text is more than 25 characters..."
    );
    expect(checkbox).toBeChecked();

    const submitButton = await screen.findByRole("button", {
      name: /submit review/i,
    });
    expect(submitButton).toBeEnabled();
    await user.click(submitButton);

    // expect a success toast message
    await screen.findByText("Your review was submitted to CritiqueBrainz!");
    expect(submitReviewSpy).toHaveBeenCalledWith("FNORD", "never_gonna", {
      entity_name: "Criminal",
      entity_id: "2bf47421-2344-4255-a525-e7d7f54de742",
      entity_type: "recording",
      languageCode: "en",
      rating: undefined,
      text: "This review text is more than 25 characters...",
    });
  });

  it("shows a message if text content is too short and prevents submission", async () => {
    renderWithProviders(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    act(() => {
      NiceModal.show(CBReviewModal, { ...props });
    });
    const checkbox = await screen.findByRole("checkbox");
    const textInput = await screen.findByRole("textbox");
    const submitButton = await screen.findByRole("button", {
      name: /submit review/i,
    });

    await user.click(checkbox);
    await user.type(textInput, "Too short!");
    // Submit button should be disabled
    expect(submitButton).toBeDisabled();

    // Try to click anyway, shouldn't do anything
    await user.click(submitButton);
    expect(submitReviewToCBSpy).not.toHaveBeenCalled();

    // expect a visible validation message
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /your review needs to be longer than/i
    );
  });

  it("prevents submission if there is no entity to review", async () => {
    renderWithProviders(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    act(() => {
      NiceModal.show(CBReviewModal, {
        listen: {
          listened_at: 0,
          track_metadata: { artist_name: "Bob", track_name: "FNORD" },
        },
      });
    });
    const checkbox = screen.queryByRole("checkbox");
    const textInput = screen.queryByRole("textbox");
    const submitButton = screen.queryByRole("button", {
      name: /submit review/i,
    });

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
    renderWithProviders(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    act(() => {
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

    await screen.findByRole("button", {
      name: "The Essential Britney Spears (release group)",
    });
  });
  it("getRecordingMBIDFromTrack calls API and returns the correct recording MBID", async () => {
    const mbid = "0255f1ea-3199-49b4-8b5c-bdcc3716ebc9";
    renderWithProviders(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    act(() => {
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
    await waitFor(() => {
      expect(lookupMBReleaseFromTrackSpy).toHaveBeenCalledTimes(1);
      return expect(lookupMBReleaseFromTrackSpy).toHaveBeenCalledWith(mbid);
    });

    const selectRecordingButton = await screen.findAllByRole("button", {
      name: "Criminal (recording)",
    });
    expect(selectRecordingButton).toHaveLength(2);
  });

  it("retries once if API throws invalid token error", async () => {
    // The modal closes upon successful submission, which messes up the following test
    // Isolate this modal from other tests
    const apiService = new APIService("FOO");
    // mock api refreshtoken sending a new token
    const apiRefreshSpy = jest
      .spyOn(apiService, "refreshAccessToken")
      .mockResolvedValue("this is new token");
    const submitReviewSpy = jest
      .spyOn(apiService, "submitReviewToCB")
      .mockRejectedValueOnce({ message: "invalid_token" })
      .mockResolvedValue({
        metadata: { review_id: "new-review-id-that-API-returns" },
      });

    NiceModal.register("cb-modal-2", CBReviewModal);

    renderWithProviders(<NiceModal.Provider />, {
      APIService: apiService,
    });
    act(() => {
      NiceModal.show("cb-modal-2", { ...props, keepMounted: true });
    });

    const textInput = await screen.findByRole("textbox");
    const checkbox = await screen.findByRole("checkbox");
    await user.click(checkbox);
    expect(checkbox).toBeChecked();
    await user.type(
      textInput,
      "This review text is more than 25 characters..."
    );
    const submitButton = await screen.findByRole("button", {
      name: /submit review/i,
    });
    expect(submitButton).toBeEnabled();

    await user.click(submitButton);

    // expect a success toast message eventually
    await screen.findByText("Your review was submitted to CritiqueBrainz!");

    expect(apiRefreshSpy).toHaveBeenCalledTimes(1); // a new token is requested once
    expect(apiRefreshSpy).toHaveBeenCalledWith("critiquebrainz");

    // new token was received, and the submission retried
    expect(submitReviewSpy).toHaveBeenCalledTimes(2);
  });

  it("catches API call errors and displays it on screen", async () => {
    submitReviewToCBSpy
      .mockRejectedValueOnce({
        message: "Computer says no!",
      })
      .mockResolvedValueOnce({
        metadata: { review_id: "new-review-id-that-API-returns" },
      });

    renderWithProviders(<NiceModal.Provider />, {
      APIService: testAPIService,
    });
    act(() => {
      NiceModal.show(CBReviewModal, { ...props });
    });

    await user.click(await screen.findByRole("checkbox"));
    await user.type(
      await screen.findByRole("textbox"),
      "This review text is more than 25 characters..."
    );

    const submitButton = await screen.findByRole("button", {
      name: /submit review/i,
    });
    expect(submitButton).toBeEnabled();

    await user.click(submitButton);

    // expect error toast message eventually
    await screen.findByText("Error while submitting review to CritiqueBrainz");
    expect(submitReviewToCBSpy).toHaveBeenCalled();
  });
});
