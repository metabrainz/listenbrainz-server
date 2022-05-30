import * as React from "react";
import {mount} from "enzyme";

import ListenFeedbackComponent, {
  ListenFeedbackComponentProps,
} from "../../src/listens/ListenFeedbackComponent";
import APIServiceClass from "../../src/utils/APIService";
import GlobalAppContext from "../../src/utils/GlobalAppContext";
// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const listen: Listen = {
  listened_at: 0,
  playing_now: false,
  track_metadata: {
    artist_name: "Moondog",
    track_name: "Bird's Lament",
    additional_info: {
      release_mbid: "foo",
      recording_msid: "bar",
      artist_msid: "artist_msid",
      recording_mbid: "yyyy",
      artist_mbids: ["xxxx"],
    },
  },
  user_name: "test",
};

const props: ListenFeedbackComponentProps = {
  listen,
  currentFeedback: 1,
  updateFeedbackCallback: () => {},
  newAlert: () => {},
};

const globalProps = {
  APIService: new APIServiceClass(""),
  currentUser: { auth_token: "baz", name: "test" },
  spotifyAuth: {},
  youtubeAuth: {},
};

describe("ListenFeedbackComponent", () => {
  describe("submitFeedback", () => {
    it("calls API, updates feedback state and calls updateFeedbackCallback correctly", async () => {
      const wrapper = mount<ListenFeedbackComponent>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenFeedbackComponent
            {...{ ...props, updateFeedbackCallback: jest.fn() }}
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "submitFeedback");
      spy.mockImplementation(() => Promise.resolve(200));

      await instance.submitFeedback(-1);

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("baz", -1, "bar", "yyyy");

      expect(instance.props.updateFeedbackCallback).toHaveBeenCalledTimes(1);
      expect(instance.props.updateFeedbackCallback).toHaveBeenCalledWith(
        "bar",
        -1,
        "yyyy"
      );
    });

    it("does nothing if CurrentUser.authtoken is not set", async () => {
      const wrapper = mount<ListenFeedbackComponent>(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            currentUser: { auth_token: undefined, name: "test" },
          }}
        >
          <ListenFeedbackComponent
            {...{ ...props, updateFeedbackCallback: jest.fn() }}
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "submitFeedback");
      spy.mockImplementation(() => Promise.resolve(200));

      instance.submitFeedback(-1);
      expect(spy).toHaveBeenCalledTimes(0);
    });

    it("doesn't update feedback state or call updateFeedbackCallback if status code is not 200", async () => {
      const wrapper = mount<ListenFeedbackComponent>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenFeedbackComponent {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      props.updateFeedbackCallback = jest.fn();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "submitFeedback");
      spy.mockImplementation(() => Promise.resolve(201));

      instance.submitFeedback(-1);

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("baz", -1, "bar", "yyyy");

      expect(props.updateFeedbackCallback).toHaveBeenCalledTimes(0);
    });

    it("calls handleError if error is returned", async () => {
      const newAlertSpy = jest.fn();
      const wrapper = mount<ListenFeedbackComponent>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenFeedbackComponent {...props} newAlert={newAlertSpy} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const error = new Error("my error message");
      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "submitFeedback");
      spy.mockImplementation(() => {
        throw error;
      });

      instance.submitFeedback(-1);
      expect(newAlertSpy).toHaveBeenCalledTimes(1);
      expect(newAlertSpy).toHaveBeenCalledWith(
        "danger",
        "Error while submitting feedback",
        "my error message"
      );
    });
  });
});
