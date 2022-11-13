import * as React from "react";
import { act } from "react-dom/test-utils";

import { mount } from "enzyme";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";

import FreshReleases from "../../src/fresh-releases/FreshReleases";
import ReleaseFilters from "../../src/fresh-releases/ReleaseFilters";

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

// From https://github.com/enzymejs/enzyme/issues/2073
const waitForComponentToPaint = async (wrapper: any) => {
  await act(async () => {
    // eslint-disable-next-line no-promise-executor-return
    await new Promise((resolve) => setTimeout(resolve));
    wrapper.update();
  });
};

describe("FreshReleases", () => {
  it("renders filters, card grid, and timeline components on the page", async () => {
    const mockFetchSitewideFreshReleases = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        json: () => sitewideData,
      });
    });
    mountOptions.context.APIService.fetchSitewideFreshReleases = mockFetchSitewideFreshReleases;
    const wrapper = mount(
      <GlobalAppContext.Provider value={{ ...mountOptions.context }}>
        <FreshReleases {...props} />
      </GlobalAppContext.Provider>
    );
    await waitForComponentToPaint(wrapper);
    expect(mockFetchSitewideFreshReleases).toBeCalled();
    expect(wrapper.find(ReleaseFilters)).toHaveLength(1);
    expect(wrapper.html()).toMatchSnapshot();
  });

  it("renders user fresh releases page correctly", async () => {
    const mockFetchUserFreshReleases = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        json: () => userData,
      });
    });
    mountOptions.context.APIService.fetchUserFreshReleases = mockFetchUserFreshReleases;
    const wrapper = mount(
      <GlobalAppContext.Provider value={{ ...mountOptions.context }}>
        <FreshReleases {...props} />
      </GlobalAppContext.Provider>
    );
    await waitForComponentToPaint(wrapper);

    // TODO set pageType to "user" before uncommenting the following code

    // expect(mockFetchUserFreshReleases).toBeCalled();
    // expect(wrapper.html()).toMatchSnapshot();
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
