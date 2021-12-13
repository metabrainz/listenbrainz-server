import * as React from "react";
import { mount } from "enzyme";

import Card from "../../src/utils/Card";

describe("Card", () => {
  it("renders correctly", () => {
    const wrapper = mount(<Card>Test</Card>);
    expect(wrapper).toMatchSnapshot();
  });
});
