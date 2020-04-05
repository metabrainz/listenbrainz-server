// TODO: Make the code ESLint compliant
import React from "react";
import { shallow } from "enzyme";

import LastFmImporter from "./lastFmImporter";
import Importer from "./importer";

jest.mock("./importer");

let wrapper = null;
describe("LastFmImporter Page", () => {
  beforeEach(() => {
    // Clear previous mocks
    Importer.mockClear();

    // Mount each time
    wrapper = shallow(<LastFmImporter />);
  });

  it("renders without crashing", () => {
    expect(wrapper).toBeTruthy();
  });

  it("modal renders when button clicked", () => {
    // Simulate submiting the form
    wrapper.find("form").simulate("submit", {
      preventDefault: () => null,
    });

    // Test if the show property has been set to true
    expect(wrapper.exists("Modal")).toBe(true);
  });

  it("submit button is disabled when input is empty", () => {
    // Make sure that the input is empty
    wrapper.setState({ lastfmUsername: "" });

    // Test if button is disabled
    expect(wrapper.find('input[type="submit"]').props().disabled).toBe(true);
  });
});
