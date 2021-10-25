/* eslint-disable jest/no-disabled-tests */

import * as React from "react";
import { mount } from "enzyme";
import { GlobalAppContextT } from "../GlobalAppContext";
import APIService from "../APIService";
import BrainzPlayer from "../BrainzPlayer";
import * as colorPlayProps from "../__mocks__/colorPlayProps.json";
import ColorPlay from "./ColorPlay";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

// typescript doesn't recognise string literal values
const props = {
  ...colorPlayProps,
  newAlert: () => {},
};

// Create a new instance of GlobalAppContext
const mountOptions: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIService("foo"),
    youtubeAuth: colorPlayProps.youtube as YoutubeUser,
    spotifyAuth: colorPlayProps.spotify as SpotifyUser,
    currentUser: colorPlayProps.user,
  },
};

describe("ColorPlay", () => {

  it("contains a BrainzPlayer instance", () => {
    const wrapper = mount<ColorPlay>(<ColorPlay {...props} />, mountOptions);
    const instance = wrapper.instance();
    expect(wrapper.find(BrainzPlayer)).toHaveLength(1);
  });

});


describe("selectRelease", () => {
  it("selects the particular release and starts playing it in brainzplayer", async () => {
    const wrapper = mount<ColorPlay>(<ColorPlay {...props} />, mountOptions);
    const instance = wrapper.instance();
   
  });
});
