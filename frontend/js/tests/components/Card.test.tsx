import * as React from "react";
import { mount } from "enzyme";

import Card from "../../src/components/Card";

describe("Card", () => {
  it("renders correctly", () => {
    const wrapper = mount(<Card>Test</Card>);
    expect(wrapper.find(".card")).toHaveLength(1);
  });
});
