import React from "react";
import { shallow } from "enzyme";

import LastFMImporterModal from "./LastFMImporterModal";

const props = {
  disable: false,
  children: [],
  onClose: (event: React.MouseEvent<HTMLButtonElement>) => {},
}
describe("LastFmImporterModal", () => {
  it("renders without crashing", () => {
    const wrapper = shallow(<LastFMImporterModal {...props} />);
    expect(wrapper).toBeTruthy();
  });

  it("close button is disabled/enabled based upon props", () => {
    const wrapper = shallow(<LastFMImporterModal {...props} />);
    // Test if close button is disabled
    wrapper.setProps({ disable: true });
    expect(wrapper.find("button").props().disabled).toBe(true);

    // Test if close button is enabled
    wrapper.setProps({ disable: false });
    expect(wrapper.find("button").props().disabled).toBe(false);
  });
});
