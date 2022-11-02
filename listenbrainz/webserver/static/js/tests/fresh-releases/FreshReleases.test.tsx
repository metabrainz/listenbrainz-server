import * as React from "react";

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

describe("FreshReleases", () => {
  it("renders the page correctly", () => {
    // This seems to be working.
    // TODO take forward from here :D
    const fakeAPIService = new APIService("foo");
    const mockFetchSitewideFreshReleases = jest.fn()
    fakeAPIService.fetchSitewideFreshReleases = mockFetchSitewideFreshReleases
    const wrapper = mount(
      <GlobalAppContext.Provider value={{...mountOptions.context, APIService: fakeAPIService}}>
        <FreshReleases {...props} />
      </GlobalAppContext.Provider>
    );
    expect(mockFetchSitewideFreshReleases).toHaveBeenCalled()
  })
})