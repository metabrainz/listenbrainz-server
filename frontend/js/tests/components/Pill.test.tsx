import * as React from "react";
import { mount } from "enzyme";

import Pill from "../../src/components/Pill";

describe("Pill", () => {
  it("renders correctly for primary active", () => {
    const wrapper = mount(<Pill active type="primary" />);
    expect(wrapper.getDOMNode()).toContainHTML(
      '<button type="button" class="pill  active "></button>'
    );
  });

  it("renders correctly for secondary active", () => {
    const wrapper = mount(<Pill active type="secondary" />);
    expect(wrapper.getDOMNode()).toContainHTML(
      '<button type="button" class="pill secondary active "></button>'
    );
  });

  it("renders correctly for inactive", () => {
    const wrapper = mount(<Pill />);
    expect(wrapper.getDOMNode()).toContainHTML(
      '<button type="button" class="pill   "></button>'
    );
  });
});
