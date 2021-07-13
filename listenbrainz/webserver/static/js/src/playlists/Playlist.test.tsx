import * as React from "react";
import { shallow, mount } from "enzyme";
import * as timeago from "time-ago";
import AsyncSelect from "react-select/async";
import PlaylistPage from "./Playlist";
import * as playlistPageProps from "../__mocks__/playlistPageProps.json";
import GlobalAppContext, { GlobalAppContextT } from "../GlobalAppContext";
import APIService from "../APIService";
// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const {
  labsApiUrl,
  currentUser,
  playlist,
  webSocketsServerUrl,
} = playlistPageProps;

const props = {
  labsApiUrl,
  playlist: playlist as JSPFObject,
  webSocketsServerUrl,
  newAlert: () => {},
};

const GlobalContextMock: GlobalAppContextT = {
  APIService: new APIService("foo"),
  youtubeAuth: {
    api_key: "fake-api-key",
  },
  spotifyAuth: {
    access_token: "heyo",
    permission: ["streaming"] as Array<SpotifyPermission>,
  },
  currentUser,
};

describe("PlaylistPage", () => {
  it("renders correctly", () => {
    // Mock timeago (returns an elapsed time string) otherwise snapshot won't match
    timeago.ago = jest.fn().mockImplementation(() => "1 day ago");
    const wrapper = shallow<PlaylistPage>(<PlaylistPage {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
  });
  it("does not clear the add-a-track input on blur", async () => {
    const wrapper = mount<PlaylistPage>(<PlaylistPage {...props} />, {
      wrappingComponent: GlobalAppContext.Provider,
      wrappingComponentProps: {
        value: GlobalContextMock,
      },
    });
    const instance = wrapper.instance();
    let searchInput = wrapper.find(AsyncSelect);

    expect(instance.state.searchInputValue).toEqual("");
    // @ts-ignore
    expect(searchInput.props().inputValue).toEqual("");

    searchInput.simulate("focus");
    instance.handleInputChange("mysearch", { action: "input-change" });
    wrapper.update();

    expect(instance.state.searchInputValue).toEqual("mysearch");
    searchInput = wrapper.find(AsyncSelect);

    // @ts-ignore
    expect(searchInput.props().inputValue).toEqual("mysearch");

    // simulate ReactSelect input blur event
    searchInput.simulate("blur");
    instance.handleInputChange("", { action: "input-blur" });
    wrapper.update();

    searchInput = wrapper.find(AsyncSelect);
    expect(instance.state.searchInputValue).toEqual("mysearch");
    // @ts-ignore
    expect(searchInput.props().inputValue).toEqual("mysearch");

    // simulate ReactSelect menu close event (blur)
    instance.handleInputChange("", { action: "menu-close" });
    wrapper.update();

    searchInput = wrapper.find(AsyncSelect);
    expect(instance.state.searchInputValue).toEqual("mysearch");
    // @ts-ignore
    expect(searchInput.props().inputValue).toEqual("mysearch");
  });
});
