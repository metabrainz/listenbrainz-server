import * as React from "react";
import { mount } from "enzyme";

import SpotifyPlayer from "./SpotifyPlayer";
import APIService from "./APIService";

const props = {
  spotifyUser: {
    access_token: "heyo",
    permission: "read" as SpotifyPermission,
  },
  direction: "up" as SpotifyPlayDirection,
  onPermissionError: (message: string) => {},
  onCurrentListenChange: (listen: Listen) => {},
  newAlert: (
    type: AlertType,
    title: string,
    message: string | JSX.Element
  ) => {},
  apiService: new APIService("base-uri"),
  onAccountError: (message: string | JSX.Element) => {},
  listens: [],
};

describe("SpotifyPlayer", () => {
  it("renders", () => {
    window.fetch = jest.fn();
    const wrapper = mount(<SpotifyPlayer {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
  });
});
