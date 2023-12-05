import * as React from "react";
import { mount, ReactWrapper } from "enzyme";
import { act } from "react-dom/test-utils";
import { waitForComponentToPaint } from "../test-utils";

import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";

import FreshReleases from "../../src/explore/fresh-releases/FreshReleases";
import ReleaseFilters from "../../src/explore/fresh-releases/ReleaseFilters";
import ReleaseTimeline from "../../src/explore/fresh-releases/ReleaseTimeline";

import * as sitewideData from "../__mocks__/freshReleasesSitewideData.json";
import * as userData from "../__mocks__/freshReleasesUserData.json";
import * as sitewideFilters from "../__mocks__/freshReleasesSitewideFilters.json";
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";

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

// Create a new instance of GlobalAppContext
const mountOptions: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIService("foo"),
    websocketsUrl: "",
    youtubeAuth: youtube as YoutubeUser,
    spotifyAuth: spotify as SpotifyUser,
    currentUser: user,
    recordingFeedbackManager: new RecordingFeedbackManager(
      new APIService("foo"),
      { name: "Fnord" }
    ),
  },
};

describe("FreshReleases", () => {
  it("renders the page correctly", async () => {
    const mockFetchUserFreshReleases = jest.fn().mockResolvedValue({
      json: () => userData,
    });
    mountOptions.context.APIService.fetchUserFreshReleases = mockFetchUserFreshReleases;
    const wrapper = mount(
      <GlobalAppContext.Provider value={{ ...mountOptions.context }}>
        <FreshReleases />
      </GlobalAppContext.Provider>
    );
    await waitForComponentToPaint(wrapper);
    expect(mockFetchUserFreshReleases).toHaveBeenCalledWith("chinmaykunkikar");
    expect(wrapper.find(FreshReleases)).toHaveLength(1);
  });

  it("renders sitewide fresh releases page, including timeline component", async () => {
    const mockFetchSitewideFreshReleases = jest.fn().mockResolvedValue({
      json: () => sitewideData,
    });
    mountOptions.context.APIService.fetchSitewideFreshReleases = mockFetchSitewideFreshReleases;
    const wrapper = mount(
      <GlobalAppContext.Provider value={{ ...mountOptions.context }}>
        <FreshReleases />
      </GlobalAppContext.Provider>
    );
    await waitForComponentToPaint(wrapper);
    await act(() => {
      // click on sitewide-releases button
      wrapper.find("#sitewide-releases").at(0).simulate("click");
    });
    await waitForComponentToPaint(wrapper);
    expect(mockFetchSitewideFreshReleases).toHaveBeenCalledWith(3);
    expect(wrapper.find("#release-filters")).toHaveLength(1);
    expect(wrapper.find(".releases-timeline")).toHaveLength(1);
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
    wrapper.find("#filters-item-0").simulate("click");
    expect(setFilteredList).toBeCalled();
  });
});
