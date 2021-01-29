import { enableFetchMocks } from "jest-fetch-mock";
import * as React from "react";
import { shallow } from "enzyme";
import PlaylistPage from "./Playlist";
import * as playlistPageProps from "../__mocks__/playlistPageProps.json";

enableFetchMocks();

const {
  apiUrl,
  currentUser,
  playlist,
  webSocketsServerUrl,
} = playlistPageProps;

const props = {
  apiUrl,
  playlist: playlist as JSPFObject,
  spotify: {
    access_token: "heyo",
    permission: "streaming" as SpotifyPermission,
  },
  currentUser,
  webSocketsServerUrl,
};

describe("PlaylistPage", () => {
  it("renders correctly", () => {
    const wrapper = shallow<PlaylistPage>(<PlaylistPage {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
  });
  it("does not clear the add-a-track input on blur", async () => {
    const wrapper = shallow<PlaylistPage>(<PlaylistPage {...props} />);
    const instance = wrapper.instance();
    let searchInput = wrapper.find(".search");
    expect(instance.state.searchInputValue).toEqual("");
    // @ts-ignore
    expect(searchInput.props().inputValue).toEqual("");

    searchInput.simulate("focus");
    instance.handleInputChange("mysearch", { action: "input-change" });

    expect(instance.state.searchInputValue).toEqual("mysearch");
    searchInput = wrapper.find(".search");
    // @ts-ignore
    expect(searchInput.props().inputValue).toEqual("mysearch");

    // simulate ReactSelect input blur event
    searchInput.simulate("blur");
    instance.handleInputChange("", { action: "input-blur" });

    searchInput = wrapper.find(".search");
    expect(instance.state.searchInputValue).toEqual("mysearch");
    // @ts-ignore
    expect(searchInput.props().inputValue).toEqual("mysearch");

    // simulate ReactSelect menu close event (blur)
    instance.handleInputChange("", { action: "menu-close" });

    searchInput = wrapper.find(".search");
    expect(instance.state.searchInputValue).toEqual("mysearch");
    // @ts-ignore
    expect(searchInput.props().inputValue).toEqual("mysearch");
  });
});
