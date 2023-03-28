import * as React from "react";
import { mount, ReactWrapper, shallow, ShallowWrapper } from "enzyme";
import { act } from "react-dom/test-utils";
import NiceModal, { NiceModalHocProps } from "@ebay/nice-modal-react";
import { merge } from "lodash";
import APIServiceClass from "../../src/utils/APIService";
import GlobalAppContext from "../../src/utils/GlobalAppContext";

import * as lookupMBRelease from "../__mocks__/lookupMBRelease.json";
import * as lookupMBReleaseFromTrack from "../__mocks__/lookupMBReleaseFromTrack.json";

import CBReviewModal, {
  CBReviewModalProps,
} from "../../src/cb-review/CBReviewModal";
import { waitForComponentToPaint } from "../test-utils";

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

const testAPIService = new APIServiceClass("");
const globalProps = {
  APIService: testAPIService,
  currentUser: {
    id: 1,
    name: "jdaok",
    auth_token: "auth_token",
  },
  spotifyAuth: {},
  youtubeAuth: {},
  critiquebrainzAuth: {
    access_token: "BL9f6rv8OXyR0qLucXoftqAhMarEcfhUXpZ8lXII",
  },
};
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

const newAlert = jest.fn();

const props: CBReviewModalProps = {
  listen,
  newAlert,
};

const niceModalProps: NiceModalHocProps = {
  id: "fnord",
  defaultVisible: true,
};

describe("CBReviewModal", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });
  it("renders the modal correctly", async () => {
    const wrapper = mount(
      <GlobalAppContext.Provider value={globalProps}>
        <NiceModal.Provider>
          <CBReviewModal {...niceModalProps} {...props} />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    );

    expect(wrapper.html()).toMatchSnapshot();
  });

  it("submits the review and displays a success alert", async () => {
    const wrapper = mount(
      <GlobalAppContext.Provider value={globalProps}>
        <NiceModal.Provider>
          <CBReviewModal {...niceModalProps} {...props} />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    );

    await waitForComponentToPaint(wrapper);
    await act(() => {
      const textInputArea = wrapper.find("#review-text").first();
      const checkbox = wrapper.find("#acceptLicense").first();
      // simulate writing in the textInput area
      textInputArea.simulate("change", {
        target: { value: "This review text is more than 25 characters..." },
      });
      // simulate checking the accept license box
      checkbox.simulate("change", {
        target: { checked: true, type: "checkbox" },
      });
    });
    await waitForComponentToPaint(wrapper);
    const textInputArea = wrapper.find("#review-text").first();
    const checkbox = wrapper.find("#acceptLicense").first();

    expect(textInputArea.props().value).toEqual(
      "This review text is more than 25 characters..."
    );
    expect(checkbox.props().checked).toEqual(true);
    const submitButton = wrapper.find("#submitReviewButton").first();
    expect(submitButton.props().disabled).toEqual(false);

    await act(() => {
      // Simulate submiting the form
      wrapper.find("form").first().simulate("submit");
    });
    await waitForComponentToPaint(wrapper);
    expect(submitReviewToCBSpy).toHaveBeenCalledWith("jdaok", "auth_token", {
      entity_name: "Criminal",
      entity_id: "2bf47421-2344-4255-a525-e7d7f54de742",
      entity_type: "recording",
      languageCode: "en",
      rating: undefined,
      text: "This review text is more than 25 characters...",
    });
    expect(newAlert).toHaveBeenCalledWith(
      "success",
      "Your review was submitted to CritiqueBrainz!",
      <a
        href="https://critiquebrainz.org/review/new-review-id-that-API-returns"
        target="_blank"
        rel="noopener noreferrer"
      >
        Britney Spears - Criminal
      </a>
    );
  });

  describe("getGroupMBIDFromRelease", () => {
    it("calls API and returns the correct release group MBID", async () => {
      const releaseMBID = "40ef0ae1-5626-43eb-838f-1b34187519bf";
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <CBReviewModal
              {...niceModalProps}
              {...props}
              listen={merge({}, listen, {
                track_metadata: {
                  additional_info: {
                    release_group_mbid: null,
                    release_mbid: releaseMBID,
                  },
                },
              })}
            />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );
      await waitForComponentToPaint(wrapper);

      expect(lookupMBReleaseSpy).toHaveBeenCalledTimes(1);
      expect(lookupMBReleaseSpy).toHaveBeenCalledWith(releaseMBID);

      /** Can't get this to work ! Enzyme doesn't really support the useEffect hooks and
       * does not re-render the component after the entityToReview state gets updated
       */
      // const realeaseGroupMBID = "9ecc1aea-289d-4d03-b476-6bbcd1e749d7";
      // const selectRGButton = wrapper.find(
      //   "button[name='select-release-group']"
      // );
      // expect(selectRGButton).toHaveLength(1);
      // expect(selectRGButton.key()).toEqual(realeaseGroupMBID);
    });
  });

  describe("getRecordingMBIDFromTrack", () => {
    it("calls API and returns the correct recording MBID", async () => {
      const mbid = "0255f1ea-3199-49b4-8b5c-bdcc3716ebc9";
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <CBReviewModal
              {...niceModalProps}
              {...props}
              listen={merge({}, listen, {
                track_metadata: {
                  additional_info: {
                    track_mbid: mbid,
                    recording_mbid: null,
                  },
                },
              })}
            />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );
      await waitForComponentToPaint(wrapper);

      expect(lookupMBReleaseFromTrackSpy).toHaveBeenCalledTimes(1);
      expect(lookupMBReleaseFromTrackSpy).toHaveBeenCalledWith(mbid);
      /** Can't get this to work ! Enzyme doesn't really support the useEffect hooks and
       * does not re-render the component after the entityToReview state gets updated
       */
      // const selectRecordingButton = wrapper.find(
      //   "button[name='select-recording']"
      // );
      // expect(selectRecordingButton).toHaveLength(1);
      // expect(selectRecordingButton.key()).toEqual(mbid);
    });
  });

  describe("submitReviewToCB", () => {
    it("can't submit if user hasn't authenticated with CritiqueBrainz", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            critiquebrainzAuth: {}, // not authenticated
          }}
        >
          <NiceModal.Provider>
            <CBReviewModal {...niceModalProps} {...props} />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );

      expect(wrapper.find("#review-text")).toHaveLength(0);
      expect(wrapper.find("#acceptLicense")).toHaveLength(0);
      expect(wrapper.find("form")).toHaveLength(1);

      await waitForComponentToPaint(wrapper);

      await act(() => {
        // Simulate submiting the form
        wrapper.find("form").first().simulate("submit");
      });
      expect(submitReviewToCBSpy).not.toHaveBeenCalled();
    });

    it("does nothing if license was not accepted", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <CBReviewModal {...niceModalProps} {...props} />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );

      await act(() => {
        const textInputArea = wrapper.find("#review-text").first();
        // simulate writing in the textInput area
        textInputArea.simulate("change", {
          target: { value: "This review text is more than 25 characters..." },
        });
      });
      await waitForComponentToPaint(wrapper);
      const checkbox = wrapper.find("#acceptLicense").first();
      expect(checkbox.props().checked).toEqual(false);
      const submitButton = wrapper.find("button[type='submit']").first();
      expect(submitButton.props().disabled).toEqual(true);

      await act(() => {
        // Simulate submiting the form
        wrapper.find("form").first().simulate("submit");
      });

      expect(submitReviewToCBSpy).not.toHaveBeenCalled();
    });

    it("does nothing if entityToReview is null", async () => {
      // Listen empty of data won't be able to find an entity to review
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <CBReviewModal
              {...niceModalProps}
              {...props}
              listen={{
                listened_at: 0,
                track_metadata: { artist_name: "Bob", track_name: "FNORD" },
              }}
            />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );

      await waitForComponentToPaint(wrapper);
      expect(wrapper.find("button[type='submit']")).toHaveLength(0);
      expect(wrapper.find("#no-entity")).toHaveLength(1);
      expect(wrapper.find("#no-entity").first().text()).toContain(
        "We could not link FNORD by Bob to any recording, artist, or release group on MusicBrainz."
      );
      wrapper.find("form").simulate("submit");

      expect(submitReviewToCBSpy).not.toHaveBeenCalled();
    });

    it("shows an alert message and doesn't submit if textContent is too short", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <CBReviewModal {...niceModalProps} {...props} />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );
      await waitForComponentToPaint(wrapper);
      await act(() => {
        const textInputArea = wrapper.find("#review-text").first();
        const checkbox = wrapper.find("#acceptLicense").first();
        // simulate writing in the textInput area
        textInputArea.simulate("change", {
          target: { value: "Too short" },
        });
        // simulate checking the accept license box
        checkbox.simulate("change", {
          target: { checked: true, type: "checkbox" },
        });
      });
      await waitForComponentToPaint(wrapper);

      const submitButton = wrapper.find("button[type='submit']").first();
      expect(submitButton.props().disabled).toEqual(true);

      // alert shown
      const alert = wrapper.find("#text-too-short-alert");
      expect(alert).toHaveLength(1);
      expect(alert.text()).toEqual(
        "Your review needs to be longer than 25 characters."
      );
      await act(() => {
        // Simulate submiting the form
        wrapper.find("form").first().simulate("submit");
      });

      expect(submitReviewToCBSpy).not.toHaveBeenCalled();
    });

    it("retries once if API throws invalid token error", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <CBReviewModal {...niceModalProps} {...props} />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );

      await act(() => {
        const textInputArea = wrapper.find("#review-text").first();
        const checkbox = wrapper.find("#acceptLicense").first();
        // simulate writing in the textInput area
        textInputArea.simulate("change", {
          target: { value: "This review text is more than 25 characters..." },
        });
        // simulate checking the accept license box
        checkbox.simulate("change", {
          target: { checked: true, type: "checkbox" },
        });
      });
      await waitForComponentToPaint(wrapper);
      // mock api submit throwing invalid token error
      submitReviewToCBSpy.mockRejectedValueOnce({ message: "invalid_token" });

      await act(() => {
        // Simulate submiting the form
        wrapper.find("form").first().simulate("submit");
      });
      await waitForComponentToPaint(wrapper);
      expect(apiRefreshSpy).toHaveBeenCalledTimes(1); // a new token is requested once
      expect(apiRefreshSpy).toHaveBeenCalledWith("critiquebrainz");

      // new token was received, and the submission retried
      expect(submitReviewToCBSpy).toHaveBeenCalledTimes(2);
    });
  });
});
