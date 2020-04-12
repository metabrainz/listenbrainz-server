import * as React from "react";
import { mount, shallow } from "enzyme";

import LastFMImporterModal from "./LastFMImporterModal";

const props = {
  disable: false,
  children: [],
  onClose: (event: React.MouseEvent<HTMLButtonElement>) => {},
};

describe("LastFmImporterModal", () => {
  it("renders", () => {
    const wrapper = mount(<LastFMImporterModal {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
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
