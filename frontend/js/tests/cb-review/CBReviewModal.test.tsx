import * as React from "react";
import { mount, ReactWrapper, shallow, ShallowWrapper } from "enzyme";
import { act } from "react-dom/test-utils";
import APIServiceClass from "../../src/utils/APIService";
import GlobalAppContext from "../../src/utils/GlobalAppContext";

import * as lookupMBRelease from "../__mocks__/lookupMBRelease.json";
import * as lookupMBReleaseFromTrack from "../__mocks__/lookupMBReleaseFromTrack.json";

import CBReviewModal, {
  CBReviewModalProps,
  CBReviewModalState,
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

const differentListen: Listen = {
  track_metadata: {
    artist_name: "Marina and the Diamonds",
    release_name: "Electra Heart",
    track_name: "Primadonna",
  },
  listened_at: 1628634357,
};

const globalProps = {
  APIService: new APIServiceClass(""),
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

const props = {
  listen,
  isCurrentUser: true,
  newAlert: () => {},
};

describe("CBReviewModal", () => {
  let wrapper:
    | ReactWrapper<CBReviewModalProps, CBReviewModalState, CBReviewModal>
    | ShallowWrapper<CBReviewModalProps, CBReviewModalState, CBReviewModal>
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
  it("renders the modal correctly", async () => {
    wrapper = mount<CBReviewModal>(
      <GlobalAppContext.Provider value={globalProps}>
        <CBReviewModal {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();
    expect(wrapper.html()).toMatchSnapshot(); // no entityToReview version
    await act(async () => {
      await instance.componentDidMount(); // updates entityToReview
    });
    expect(wrapper.html()).toMatchSnapshot(); // valid entityToReview version
  });

  it("contains working form components that setState and call functions", async () => {
    wrapper = mount<CBReviewModal>(
      <GlobalAppContext.Provider value={globalProps}>
        <CBReviewModal {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();
    const submitReviewToCBSpy = jest.fn();
    instance.context.APIService.submitReviewToCB = submitReviewToCBSpy;
    await act(async () => {
      await instance.componentDidMount();
    });

    await waitForComponentToPaint(wrapper);
    // check review state is set to default
    expect(wrapper.state("textContent")).toEqual("");
    expect(wrapper.state("acceptLicense")).toEqual(false);

    const textInputArea = wrapper.find("#review-text").first();
    const checkbox = wrapper.find("#acceptLicense").first();
    await act(() => {
      // simulate writing in the textInput area
      textInputArea.simulate("change", {
        target: { value: "This review text is more than 25 characters..." },
      });
      // simulate checking the accept license box
      checkbox.simulate("change", {
        target: { checked: true, type: "checkbox", name: "acceptLicense" },
      });
    });

    expect(wrapper.state("loading")).toEqual(false);
    expect(wrapper.state("textContent")).toEqual(
      "This review text is more than 25 characters..."
    );
    expect(wrapper.state("acceptLicense")).toEqual(true);

    await act(() => {
      // Simulate submiting the form
      wrapper!.find("form").simulate("submit");
    });
    expect(submitReviewToCBSpy).toHaveBeenCalled();
  });
  describe("componentDidUpdate", () => {
    it("resets the state if the listen prop has changed", async () => {
      wrapper = shallow<CBReviewModal>(<CBReviewModal {...props} />);
      const instance = wrapper.instance();
      await act(async () => {
        instance.setState({ textContent: "This should go away", rating: 5 });
        wrapper!.setProps({ listen: differentListen });
      });

      // the state should now be reset to default
      expect(wrapper.state("rating")).toEqual(0);
      expect(wrapper.state("textContent")).toEqual("");
    });
  });

  describe("refreshCritiquebrainzToken", () => {
    it("calls API with the correct parameters", async () => {
      wrapper = mount<CBReviewModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <CBReviewModal {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const spy = jest.fn();
      instance.context.APIService.refreshAccessToken = spy;
      await act(async () => {
        instance.refreshCritiquebrainzToken();
      });
      expect(spy).toHaveBeenCalledWith("critiquebrainz");
    });
  });

  describe("getGroupMBIDFromRelease", () => {
    wrapper = mount<CBReviewModal>(
      <GlobalAppContext.Provider value={globalProps}>
        <CBReviewModal {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();

    it("calls API and returns the correct groupMBID string", async () => {
      const mbid = "40ef0ae1-5626-43eb-838f-1b34187519bf";
      const apiSpy = jest.fn().mockImplementation(() => {
        return Promise.resolve(lookupMBRelease);
      });
      instance.context.APIService.lookupMBRelease = apiSpy;

      const result = await instance.getGroupMBIDFromRelease(mbid);

      expect(apiSpy).toHaveBeenCalledTimes(1);
      expect(apiSpy).toHaveBeenCalledWith(
        "40ef0ae1-5626-43eb-838f-1b34187519bf"
      );
      expect(result).toEqual(lookupMBRelease["release-group"].id);
    });
  });

  describe("getRecordingMBIDFromTrack", () => {
    wrapper = mount<CBReviewModal>(
      <GlobalAppContext.Provider value={globalProps}>
        <CBReviewModal {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();

    it("calls API and returns the correct groupMBID string", async () => {
      const mbid = "0255f1ea-3199-49b4-8b5c-bdcc3716ebc9";
      const trackName = "Criminal";
      const apiSpy = jest.fn().mockImplementation(() => {
        return Promise.resolve(lookupMBReleaseFromTrack);
      });
      instance.context.APIService.lookupMBReleaseFromTrack = apiSpy;

      const result = await instance.getRecordingMBIDFromTrack(mbid, trackName);

      expect(apiSpy).toHaveBeenCalledTimes(1);
      expect(apiSpy).toHaveBeenCalledWith(
        "0255f1ea-3199-49b4-8b5c-bdcc3716ebc9"
      );
      expect(result).toEqual(
        lookupMBReleaseFromTrack.releases[0].media[0].tracks[11].recording.id
      );
    });
  });

  describe("submitReviewToCB", () => {
    it("calls API, and sets state + creates a new alert on success", async () => {
      const extraProps = { ...props, newAlert: jest.fn() };

      wrapper = mount<CBReviewModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <CBReviewModal {...extraProps} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      await act(async () => {
        await instance.componentDidMount(); // set valid entityToReview
      });
      await act(async () => {
        // set valid review state so submit function doesn't fail
        instance.setState({
          textContent: "String is over 25 characters",
          acceptLicense: true,
        });
      });

      const spy = jest.fn().mockResolvedValue({
        metadata: { review_id: "new review id that API returns" },
      });
      instance.context.APIService.submitReviewToCB = spy;
      await act(async () => {
        await instance.submitReviewToCB();
      });

      expect(spy).toHaveBeenCalledWith("jdaok", "auth_token", {
        entity_name: "Criminal",
        entity_id: "2bf47421-2344-4255-a525-e7d7f54de742",
        entity_type: "recording",
        languageCode: "en",
        rating: undefined,
        text: "String is over 25 characters",
      });

      expect(instance.props.newAlert).toHaveBeenCalled();

      // test that state was updated
      expect(wrapper.state("success")).toEqual(true);
      expect(wrapper.state("reviewMBID")).toEqual(
        "new review id that API returns"
      );
    });

    it("does nothing if user hasn't authenticated with CritiqueBrainz", async () => {
      wrapper = mount<CBReviewModal>(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            critiquebrainzAuth: {}, // not authenticated
          }}
        >
          <CBReviewModal {...props} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();
      await act(async () => {
        await instance.componentDidMount(); // set valid entity so submit doesn't fail from missing entity
      });
      await act(async () => {
        // set valid review state
        instance.setState({
          textContent: "String is over 25 characters",
          acceptLicense: true,
        });
      });

      const spy = jest.fn();
      instance.context.APIService.submitReviewToCB = spy;
      await act(async () => {
        await instance.submitReviewToCB(); // access token not set
      });
      expect(spy).not.toHaveBeenCalled();
    });

    it("does nothing if license was not accepted", async () => {
      wrapper = mount<CBReviewModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <CBReviewModal {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      await act(async () => {
        await instance.componentDidMount(); // set valid entity so submit doesn't fail from missing entity
      });
      await act(async () => {
        // set valid review state
        instance.setState({
          textContent: "String is over 25 characters",
          acceptLicense: false,
        });
      });

      const spy = jest.fn();
      instance.context.APIService.submitReviewToCB = spy;
      await act(async () => {
        await instance.submitReviewToCB();
      });
      expect(spy).not.toHaveBeenCalled();
    });

    it("does nothing if entityToReview is null", async () => {
      // Prevent normal call of componentDidMount which sets entityToReview based on listen
      jest
        .spyOn(CBReviewModal.prototype, "componentDidMount")
        .mockImplementationOnce((): any => {});
      wrapper = mount<CBReviewModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <CBReviewModal {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      await act(() => {
        instance.setState({
          textContent: "String is over 25 characters",
          acceptLicense: true,
        });
      });

      const spy = jest.fn();
      instance.context.APIService.submitReviewToCB = spy;
      await act(async () => {
        await instance.submitReviewToCB();
      });

      expect(wrapper.state("entityToReview")).toEqual(null);
      expect(spy).not.toHaveBeenCalled();
    });

    it("sets reviewValidateAlert state and returns if textContent does not meet length requirement", async () => {
      wrapper = mount<CBReviewModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <CBReviewModal {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      await act(async () => {
        await instance.componentDidMount();
      });

      const spy = jest.fn();
      instance.context.APIService.submitReviewToCB = spy;
      await act(async () => {
        instance.setState({
          textContent: "invalid",
          acceptLicense: true,
        });
      });

      expect(wrapper.state("reviewValidateAlert")).toEqual(null); // no alert before submitting
      await act(async () => {
        await instance.submitReviewToCB();
      });
      expect(spy).not.toHaveBeenCalled();
      expect(wrapper.state("reviewValidateAlert")).toEqual(
        // alert shown
        "Your review needs to be longer than 25 characters."
      );
    });

    it("retries once if API throws invalid token error", async () => {
      wrapper = mount<CBReviewModal>(
        <GlobalAppContext.Provider value={globalProps}>
          <CBReviewModal {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      await act(async () => {
        await instance.componentDidMount();
      });
      await act(async () => {
        instance.setState({
          textContent: "String is over 25 characters",
          acceptLicense: true,
        });
      });

      // mock api submit throwing invalid token error
      instance.context.APIService.submitReviewToCB = jest
        .fn()
        .mockImplementation(() => {
          const error = new Error();
          error.message = "invalid_token";
          throw error;
        });

      // mock api refreshtoken sending a new token
      instance.context.APIService.refreshCritiquebrainzToken = jest
        .fn()
        .mockImplementation(() => Promise.resolve("this is new token"));

      const instanceSubmitSpy = jest.spyOn(instance, "submitReviewToCB");
      const instanceRefreshSpy = jest.spyOn(
        instance,
        "refreshCritiquebrainzToken"
      );
      await act(async () => {
        await instance.submitReviewToCB(); // this call fails, so...
      });

      expect(instanceRefreshSpy).toHaveBeenCalledTimes(1); // a new token is requested once
      // new token was recieved, and no more retires
      expect(instanceSubmitSpy).toHaveBeenLastCalledWith(
        undefined,
        "this is new token",
        0
      );
    });
  });
});
