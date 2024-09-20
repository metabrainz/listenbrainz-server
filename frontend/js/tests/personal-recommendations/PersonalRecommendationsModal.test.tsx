import * as React from "react";
import { mount } from "enzyme";

import { act } from "react-dom/test-utils";
import NiceModal, { NiceModalHocProps } from "@ebay/nice-modal-react";
import PersonalRecommendationModal, {
  maxBlurbContentLength,
} from "../../src/personal-recommendations/PersonalRecommendationsModal";
import APIServiceClass from "../../src/utils/APIService";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import { waitForComponentToPaint } from "../test-utils";
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";
import { ReactQueryWrapper } from "../test-react-query";

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

const user = {
  id: 1,
  name: "name",
  auth_token: "auth_token",
};
const testAPIService = new APIServiceClass("");
const globalProps: GlobalAppContextT = {
  APIService: testAPIService,
  websocketsUrl: "",
  currentUser: user,
  spotifyAuth: {},
  youtubeAuth: {},
  recordingFeedbackManager: new RecordingFeedbackManager(testAPIService, {
    name: "Fnord",
  }),
};

const niceModalProps: NiceModalHocProps = {
  id: "fnord",
  defaultVisible: true,
};

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const getFollowersSpy = jest
  .spyOn(testAPIService, "getFollowersOfUser")
  .mockResolvedValue({
    followers: ["bob", "fnord"],
  });

const submitPersonalRecommendationSpy = jest
  .spyOn(testAPIService, "submitPersonalRecommendation")
  .mockImplementation((userToken, userName, metadata) => {
    return Promise.resolve(200);
  });

describe("PersonalRecommendationModal", () => {
  afterEach(() => {
    getFollowersSpy.mockClear();
    submitPersonalRecommendationSpy.mockClear();
  });

  describe("submitPersonalRecommendation", () => {
    it("calls API, and creates new alert on success", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <ReactQueryWrapper>
              <PersonalRecommendationModal
                {...niceModalProps}
                listenToPersonallyRecommend={listenToPersonallyRecommend}
              />
            </ReactQueryWrapper>
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );

      await waitForComponentToPaint(wrapper);

      expect(getFollowersSpy).toHaveBeenCalled();
      await act(async () => {
        const userNameInput = wrapper.find("input[type='text']").first();
        userNameInput?.simulate("change", { target: { value: "fnord" } });
      });
      await waitForComponentToPaint(wrapper);
      await act(async () => {
        const button = wrapper.find("button[title='fnord']").first();
        button?.simulate("click");
      });
      await act(async () => {
        const blurbTextArea = wrapper
          .find("textarea[name='blurb-content']")
          .first();
        blurbTextArea.simulate("change", { target: { value: "hii" } });
      });
      await act(async () => {
        const submitButton = wrapper.find("button[type='submit']").first();
        submitButton?.simulate("click");
      });
      await waitForComponentToPaint(wrapper);

      expect(submitPersonalRecommendationSpy).toHaveBeenCalledTimes(1);
      expect(submitPersonalRecommendationSpy).toHaveBeenCalledWith(
        "auth_token",
        "name",
        {
          recording_mbid: "recording_mbid",
          recording_msid: "recording_msid",
          blurb_content: "hii",
          users: ["fnord"],
        }
      );
    });

    it("does nothing if userToken not set", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            currentUser: { auth_token: undefined, id: 1, name: "test" },
          }}
        >
          <NiceModal.Provider>
            <PersonalRecommendationModal
              {...niceModalProps}
              listenToPersonallyRecommend={listenToPersonallyRecommend}
            />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );

      await act(async () => {
        const submitButton = wrapper.find("button[type='submit']").first();
        submitButton?.simulate("click");
      });
      await waitForComponentToPaint(wrapper);
      expect(submitPersonalRecommendationSpy).not.toHaveBeenCalled();
    });

    it("calls handleError in case of error", async () => {
      const error = new Error("error");
      submitPersonalRecommendationSpy.mockRejectedValueOnce(error);
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <PersonalRecommendationModal
              {...niceModalProps}
              listenToPersonallyRecommend={listenToPersonallyRecommend}
            />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );

      await waitForComponentToPaint(wrapper);
      await act(async () => {
        const userNameInput = wrapper.find("input[type='text']").first();
        userNameInput?.simulate("change", { target: { value: "fnord" } });
      });
      await waitForComponentToPaint(wrapper);
      await act(async () => {
        const button = wrapper.find("button[title='fnord']").first();
        button?.simulate("click");
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
            <PersonalRecommendationModal
              {...niceModalProps}
              listenToPersonallyRecommend={listenToPersonallyRecommend}
            />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );

      const unparsedInput =
        "This string contains \n\n line breaks and multiple   consecutive   spaces.";

      // simulate writing in the textArea
      await act(async () => {
        const blurbTextArea = wrapper
          .find("textarea[name='blurb-content']")
          .first();
        blurbTextArea.simulate("change", { target: { value: unparsedInput } });
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
            <ReactQueryWrapper>
              <PersonalRecommendationModal
                {...niceModalProps}
                listenToPersonallyRecommend={listenToPersonallyRecommend}
              />
            </ReactQueryWrapper>
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );
      await waitForComponentToPaint(wrapper);
      // simulate writing in the textArea
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
