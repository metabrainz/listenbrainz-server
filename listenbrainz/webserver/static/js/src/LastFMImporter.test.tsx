import * as React from "react";
import { shallow } from "enzyme";

import LastFmImporter from "./LastFMImporter";

const props = {
  user: {
    id: "id",
    name: "dummyUser",
    auth_token: "foobar",
  },
  profileUrl: "http://profile",
  apiUrl: "apiUrl",
  lastfmApiUrl: "http://ws.audioscrobbler.com/2.0/",
  lastfmApiKey: "foobar",
};


describe("LastFmImporter Page", () => {

  it("renders without crashing", () => {
    const wrapper = shallow(<LastFmImporter {...props}/>);
    expect(wrapper).toBeTruthy();
  });

  it("modal renders when button clicked", () => {
    const wrapper = shallow(<LastFmImporter {...props}/>);
    // Simulate submiting the form
    wrapper.find("form").simulate("submit", {
      preventDefault: () => null,
    });

    // Test if the show property has been set to true
    expect(wrapper.exists("LastFMImporterModal")).toBe(true);
  });

  it("submit button is disabled when input is empty", () => {
    const wrapper = shallow(<LastFmImporter {...props}/>);
    // Make sure that the input is empty
    wrapper.setState({ lastfmUsername: "" });

    // Test if button is disabled
    expect(wrapper.find('input[type="submit"]').props().disabled).toBe(true);
  });
});
