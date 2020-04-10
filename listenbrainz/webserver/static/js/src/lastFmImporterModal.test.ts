/* eslint-disable */
// TODO: Make the code ESLint compliant
import React from "react";
import { shallow } from "enzyme";

import LastFmImporterModal from "./lastFmImporterModal";

let wrapper = null;
describe("LastFmImporterModal", () => {
  beforeEach(() => {
    // Mount each time
    wrapper = shallow(<LastFmImporterModal />);
  });

  it("renders without crashing", () => {
    expect(wrapper).toBeTruthy();
  });

  it("close button is disabled/enabled based upon props", () => {
    // Test if close button is disabled
    wrapper.setProps({ disable: true });
    expect(wrapper.find("button").props().disabled).toBe(true);

    // Test if close button is enabled
    wrapper.setProps({ disable: false });
    expect(wrapper.find("button").props().disabled).toBe(false);
  });
});
