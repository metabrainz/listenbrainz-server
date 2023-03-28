import * as React from "react";
import { mount, ReactWrapper } from "enzyme";
import { act } from "react-dom/test-utils";
import { waitForComponentToPaint } from "../test-utils";

import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";

import FreshReleases, {
  FreshReleasesProps,
} from "../../src/explore/fresh-releases/FreshReleases";
import ReleaseFilters from "../../src/explore/fresh-releases/ReleaseFilters";

import * as sitewideData from "../__mocks__/freshReleasesSitewideData.json";
import * as userData from "../__mocks__/freshReleasesUserData.json";
import * as sitewideFilters from "../__mocks__/freshReleasesSitewideFilters.json";

const freshReleasesProps = {
  user: {
    name: "chinmaykunkikar",
    id: 1,
  },
  profileUrl: "/user/chinmaykunkikar/",
  spotify: {
    access_token: "access-token",
    permission: ["streaming", "user-read-email", "user-read-private"],
  },
  youtube: {
    api_key: "fake-api-key",
  },
};

const { youtube, spotify, user } = freshReleasesProps;

const props = {
  ...freshReleasesProps,
  newAlert: () => {},
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
  it("renders filters, card grid, and timeline components on the page", async () => {
    const mockFetchSitewideFreshReleases = jest.fn().mockResolvedValue({
      json: () => sitewideData,
    });
    mountOptions.context.APIService.fetchSitewideFreshReleases = mockFetchSitewideFreshReleases;
    const wrapper = mount(
      <GlobalAppContext.Provider value={{ ...mountOptions.context }}>
        <FreshReleases {...props} />
      </GlobalAppContext.Provider>
    );
    await waitForComponentToPaint(wrapper);
    expect(mockFetchSitewideFreshReleases).toHaveBeenCalledWith(3);
    await waitForComponentToPaint(wrapper);
    expect(wrapper.find(ReleaseFilters)).toHaveLength(1);
    expect(wrapper.html()).toMatchSnapshot();
  });

  it("renders user fresh releases page correctly", async () => {
    const mockFetchUserFreshReleases = jest.fn().mockResolvedValue({
      json: () => userData,
    });
    mountOptions.context.APIService.fetchUserFreshReleases = mockFetchUserFreshReleases;
    const wrapper = mount(
      <GlobalAppContext.Provider value={{ ...mountOptions.context }}>
        <FreshReleases {...props} />
      </GlobalAppContext.Provider>
    );
    // click on user-releases button
    wrapper.find("#user-releases").at(0).simulate("click");
    await waitForComponentToPaint(wrapper);

    expect(mockFetchUserFreshReleases).toBeCalled();
    expect(wrapper.html()).toMatchSnapshot();
  });

  it("renders filters correctly", async () => {
    const setFilteredList = jest.fn();

    const wrapper = mount(
      <ReleaseFilters
        allFilters={sitewideFilters}
        releases={sitewideData}
        setFilteredList={setFilteredList}
      />
    );

    await waitForComponentToPaint(wrapper);
    expect(wrapper.html()).toMatchSnapshot();
    wrapper.find("#filters-item-0").simulate("click");
    expect(setFilteredList).toBeCalled();
  });
});
