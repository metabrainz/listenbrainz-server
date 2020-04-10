/* eslint-disable */
// TODO: Make the code ESLint compliant
import React from "react";
import { shallow } from "enzyme";

import LastFmImporterModal from "./lastFmImporterModal";

describe("LastFmImporterModal", () => {
  it("renders without crashing", () => {
    const wrapper = shallow(<LastFmImporterModal />);
    expect(wrapper).toBeTruthy();
  });

  it("close button is disabled/enabled based upon props", () => {
    const wrapper = shallow(<LastFmImporterModal />);
    // Test if close button is disabled
    wrapper.setProps({ disable: true });
    expect(wrapper.find("button").props().disabled).toBe(true);

    // Test if close button is enabled
    wrapper.setProps({ disable: false });
    expect(wrapper.find("button").props().disabled).toBe(false);
  });
});
