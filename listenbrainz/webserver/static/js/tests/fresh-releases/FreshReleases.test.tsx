import React from "react";

import { mount } from "enzyme";
import GlobalAppContext, { GlobalAppContextT } from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";

import FreshReleases from "../../src/fresh-releases/FreshReleases";

const freshReleasesProps = {
  "user": {
    "name": "chinmaykunkikar",
    "id": 1
  },
  "profileUrl": "/user/chinmaykunkikar/",
  "spotify": {
    "access_token": "access-token",
    "permission": ["streaming", "user-read-email", "user-read-private"]
  },
  "youtube": {
    "api_key": "fake-api-key"
  }
}

const { youtube, spotify, user } = freshReleasesProps;

const props = {
  ...freshReleasesProps,
  newAlert: () => { },
};

// Create a new instance of GlobalAppContext
const mountOptions: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIService("foo"),
    youtubeAuth: youtube as YoutubeUser,
    spotifyAuth: spotify as SpotifyUser,
    currentUser: user,
  },
};

// const release: FreshReleaseItem = {
//   artist_credit_name: "clipping.",
//   artist_mbids: ["84ca8fa4-7cca-4948-a90a-cb44db29853d"],
//   caa_id: 33807384149,
//   release_date: "2022-10-12",
//   release_group_mbid: "44ce58e0-6254-4790-8fd8-0b432f3c9db1",
//   release_group_primary_type: "EP",
//   release_group_secondary_type: "Remix",
//   release_mbid: "95ff5c88-06e3-40d2-b8db-f1a03c6450b8",
//   release_name: "REMXNG 2.4"
// };

describe("FreshReleases", () => {
  it("renders the page correctly", () => {
    const wrapper = mount(
      <GlobalAppContext.Provider value={mountOptions.context}>
        <FreshReleases {...props} />
      </GlobalAppContext.Provider>
    );
    expect(wrapper.html()).toMatchSnapshot();
  })
})