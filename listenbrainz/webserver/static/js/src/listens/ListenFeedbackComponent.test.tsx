import * as React from "react";
import { mount, shallow } from "enzyme";

import ListenCard, { ListenCardProps } from "./ListenCard";
import * as utils from "../utils";
import APIServiceClass from "../APIService";
import GlobalAppContext from "../GlobalAppContext";
import RecommendationControl from "../recommendations/RecommendationControl";
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

const props: ListenCardProps = {
  listen,
  currentFeedback: 1,
  showTimestamp: true,
  showUsername: true,
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
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard {...{ ...props, updateFeedbackCallback: jest.fn() }} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "submitFeedback");
      spy.mockImplementation(() => Promise.resolve(200));

      expect(wrapper.state("feedback")).toEqual(1);

      await instance.submitFeedback(-1);

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("baz", "bar", -1);

      expect(wrapper.state("feedback")).toEqual(-1);
      expect(instance.props.updateFeedbackCallback).toHaveBeenCalledTimes(1);
      expect(instance.props.updateFeedbackCallback).toHaveBeenCalledWith(
        "bar",
        -1
      );
    });

    it("does nothing if CurrentUser.authtoken is not set", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            currentUser: { auth_token: undefined, name: "test" },
          }}
        >
          <ListenCard {...{ ...props, updateFeedbackCallback: jest.fn() }} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "submitFeedback");
      spy.mockImplementation(() => Promise.resolve(200));

      expect(wrapper.state("feedback")).toEqual(1);

      instance.submitFeedback(-1);
      expect(spy).toHaveBeenCalledTimes(0);
      expect(wrapper.state("feedback")).toEqual(1);
    });

    it("doesn't update feedback state or call updateFeedbackCallback if status code is not 200", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      props.updateFeedbackCallback = jest.fn();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "submitFeedback");
      spy.mockImplementation(() => Promise.resolve(201));

      expect(wrapper.state("feedback")).toEqual(1);

      instance.submitFeedback(-1);

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("baz", "bar", -1);

      expect(wrapper.state("feedback")).toEqual(1);
      expect(props.updateFeedbackCallback).toHaveBeenCalledTimes(0);
    });

    it("calls handleError if error is returned", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      instance.handleError = jest.fn();

      const error = new Error("error");
      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "submitFeedback");
      spy.mockImplementation(() => {
        throw error;
      });

      instance.submitFeedback(-1);
      expect(instance.handleError).toHaveBeenCalledTimes(1);
      expect(instance.handleError).toHaveBeenCalledWith(
        error,
        "Error while submitting feedback"
      );
    });
  });
});
