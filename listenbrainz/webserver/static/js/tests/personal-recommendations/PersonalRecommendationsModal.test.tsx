import * as React from "react";
import { mount, ReactWrapper } from "enzyme";

import { act } from "react-dom/test-utils";
import PersonalRecommendationModal, {
  PersonalRecommendationModalProps,
  PersonalRecommendationModalState,
} from "../../src/personal-recommendations/PersonalRecommendationsModal";
import APIServiceClass from "../../src/utils/APIService";
import GlobalAppContext from "../../src/utils/GlobalAppContext";
import { waitForComponentToPaint } from "../test-utils";

const recordingToPersonallyRecommend: Listen = {
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

const globalProps = {
  APIService: new APIServiceClass(""),
  currentUser: user,
  spotifyAuth: {},
  youtubeAuth: {},
};

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

describe("PersonalRecommendationModal", () => {
  let wrapper:
    | ReactWrapper<
        PersonalRecommendationModalProps,
        PersonalRecommendationModalState,
        PersonalRecommendationModal
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
  it("renders everything right", () => {
    wrapper = mount<PersonalRecommendationModal>(
      <PersonalRecommendationModal
        recordingToPersonallyRecommend={recordingToPersonallyRecommend}
        newAlert={jest.fn()}
      />
    );

    expect(wrapper.html()).toMatchSnapshot();
  });
  describe("submitPersonalRecommendation", () => {
    it("calls API, and creates new alert on success", async () => {
      // Prevent normal call of componentDidMount which fetches stuff and will call newAlert, which we don't want in this test
      jest
        .spyOn(PersonalRecommendationModal.prototype, "componentDidMount")
        .mockImplementationOnce((): any => {});
      wrapper = mount<PersonalRecommendationModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <PersonalRecommendationModal
            recordingToPersonallyRecommend={recordingToPersonallyRecommend}
            newAlert={jest.fn()}
          />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();
      await waitForComponentToPaint(wrapper);
      const spy = jest.spyOn(
        instance.context.APIService,
        "submitPersonalRecommendation"
      );
      spy.mockImplementation((userToken, userName, metadata) => {
        return Promise.resolve(200);
      });
      await act(async () => {
        wrapper!.setState({
          blurbContent: "hii",
          users: ["riksucks", "hrik2001"],
        });
      });
      await act(async () => {
        await instance.submitPersonalRecommendation();
      });

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("auth_token", "name", {
        recording_mbid: "recording_mbid",
        recording_msid: "recording_msid",
        artist_name: "TWICE",
        track_name: "Feel Special",
        release_name: undefined,
        blurb_content: "hii",
        users: ["riksucks", "hrik2001"],
      });
      expect(instance.props.newAlert).toHaveBeenCalledTimes(1);
    });

    it("blurbContent is reset after successful posting", async () => {
      wrapper = mount<PersonalRecommendationModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <PersonalRecommendationModal
            recordingToPersonallyRecommend={recordingToPersonallyRecommend}
            newAlert={jest.fn()}
          />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();
      const spy = jest.spyOn(
        instance.context.APIService,
        "submitPersonalRecommendation"
      );
      spy.mockImplementation((userToken, userName, metadata) => {
        return Promise.resolve(200);
      });
      await act(async () => {
        wrapper!.setState({
          blurbContent: "hii",
          users: ["riksucks", "hrik2001"],
        });
      });
      expect(wrapper.state("blurbContent")).toEqual("hii");
      expect(wrapper.state("users")).toEqual(["riksucks", "hrik2001"]);
      const setStateSpy = jest.spyOn(instance, "setState");
      await act(async () => {
        await instance.submitPersonalRecommendation();
      });
      expect(setStateSpy).toHaveBeenCalledTimes(1);
      expect(wrapper.state("blurbContent")).toEqual("");
    });

    it("does nothing if userToken not set", async () => {
      wrapper = mount<PersonalRecommendationModal>(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            currentUser: { auth_token: undefined, id: 1, name: "test" },
          }}
        >
          <PersonalRecommendationModal
            recordingToPersonallyRecommend={recordingToPersonallyRecommend}
            newAlert={jest.fn()}
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      const spy = jest.spyOn(
        instance.context.APIService,
        "submitPersonalRecommendation"
      );
      spy.mockImplementation((userToken, userName, metadata) => {
        return Promise.resolve(200);
      });

      await act(async () => {
        await instance.submitPersonalRecommendation();
      });
      expect(spy).toHaveBeenCalledTimes(0);
    });

    it("calls handleError in case of error", async () => {
      wrapper = mount<PersonalRecommendationModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <PersonalRecommendationModal
            recordingToPersonallyRecommend={recordingToPersonallyRecommend}
            newAlert={jest.fn()}
          />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();
      await waitForComponentToPaint(wrapper);
      instance.handleError = jest.fn();

      const error = new Error("error");
      const spy = jest.spyOn(
        instance.context.APIService,
        "submitPersonalRecommendation"
      );
      spy.mockImplementation((userToken, userName, metadata) => {
        throw error;
      });

      await act(async () => {
        await instance.submitPersonalRecommendation();
      });

      expect(instance.handleError).toHaveBeenCalledTimes(1);
      expect(instance.handleError).toHaveBeenCalledWith(
        error,
        "Error while recommending a track"
      );
    });
  });

  describe("handleBlurbInputChange", () => {
    it("removes line breaks and excessive spaces from input before setting blurbContent in state ", async () => {
      wrapper = mount<PersonalRecommendationModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <PersonalRecommendationModal
            recordingToPersonallyRecommend={recordingToPersonallyRecommend}
            newAlert={jest.fn()}
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const unparsedInput =
        "This string contains \n\n line breaks and multiple   consecutive   spaces.";
      const setStateSpy = jest.spyOn(instance, "setState");

      await waitForComponentToPaint(wrapper);
      // simulate writing in the textArea
      const blurbContentInput = wrapper.find("#blurb-content").first();
      await act(async () => {
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
      wrapper = mount<PersonalRecommendationModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <PersonalRecommendationModal
            recordingToPersonallyRecommend={recordingToPersonallyRecommend}
            newAlert={jest.fn()}
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      await waitForComponentToPaint(wrapper);
      // simulate writing in the textArea
      const blurbContentInput = wrapper.find("#blurb-content").first();
      await act(async () => {
        blurbContentInput.simulate("change", {
          target: { value: "This string is valid." },
        });
      });

      const invalidInputLength = "a".repeat(instance.maxBlurbContentLength + 1);
      expect(invalidInputLength.length).toBeGreaterThan(
        instance.maxBlurbContentLength
      );
      await waitForComponentToPaint(wrapper);
      const setStateSpy = jest.spyOn(instance, "setState");
      await act(async () => {
        blurbContentInput.simulate("change", {
          target: { value: invalidInputLength },
        });
      });
      await waitForComponentToPaint(wrapper);

      // blurbContent should not have changed
      expect(setStateSpy).not.toHaveBeenCalled();
      expect(wrapper.state("blurbContent")).toEqual("This string is valid.");
    });
  });

  describe("handleError", () => {
    it("calls newAlert", async () => {
      wrapper = mount<PersonalRecommendationModal>(
        <PersonalRecommendationModal
          recordingToPersonallyRecommend={recordingToPersonallyRecommend}
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
