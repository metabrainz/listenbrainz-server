import * as React from "react";
import { act } from 'react-dom/test-utils';

import { mount } from "enzyme";
import GlobalAppContext, { GlobalAppContextT } from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";

import FreshReleases from "../../src/fresh-releases/FreshReleases";

import * as freshReleasesSitewideData from "../__mocks__/freshReleasesSitewideData.json"

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

// From https://github.com/enzymejs/enzyme/issues/2073
const waitForComponentToPaint = async (wrapper: any) => {
  await act(async () => {
    await new Promise(resolve => setTimeout(resolve));
    wrapper.update();
  });
};

describe("FreshReleases", () => {

  beforeAll(() => {
    mountOptions.context.APIService.fetchSitewideFreshReleases = jest.fn().mockResolvedValue(freshReleasesSitewideData);
  });
  it("renders the page correctly", () => {
    const response = freshReleasesSitewideData
    const mockFetchSitewideFreshReleases = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 400,
        json: () => response
      });
    })
    mountOptions.context.APIService.fetchSitewideFreshReleases = mockFetchSitewideFreshReleases
    const wrapper = mount(
      <GlobalAppContext.Provider value={{ ...mountOptions.context }}>
        <FreshReleases {...props} />
      </GlobalAppContext.Provider>
    );
    waitForComponentToPaint(wrapper);
    expect(mockFetchSitewideFreshReleases).toBeCalled()
    expect(mockFetchSitewideFreshReleases.mockResolvedValue((response)))
    expect(wrapper).toMatchSnapshot()
  })
})