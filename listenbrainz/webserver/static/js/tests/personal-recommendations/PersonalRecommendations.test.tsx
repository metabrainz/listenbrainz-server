import * as React from "react";
import { mount } from "enzyme";

import PersonalRecommendationModal from "../../src/personal-recommendations/PersonalRecommendations";
import APIServiceClass from "../../src/utils/APIService";
import GlobalAppContext from "../../src/utils/GlobalAppContext";

const recordingToPersonallyRecommend: Listen = {
  listened_at: 1605927742,
  track_metadata: {
    artist_name: "TWICE",
    track_name: "Feel Special",
    additional_info: {
      release_mbid: "release_mbid",
      recording_msid: "recording_msid",
      recording_mbid: "recording_mbid",
      artist_msid: "artist_msid",
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
  it("renders everything right", () => {
    const wrapper = mount<PersonalRecommendationModal>(
      <PersonalRecommendationModal
        recordingToPersonallyRecommend={recordingToPersonallyRecommend}
        newAlert={jest.fn()}
      />
    );

    expect(wrapper.html()).toMatchSnapshot();
  });
});

describe("submitPersonalRecommendation", () => {
  it("calls API, and creates new alert on success", async () => {
    const wrapper = mount<PersonalRecommendationModal>(
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

    await instance.submitPersonalRecommendation();
  });
});
