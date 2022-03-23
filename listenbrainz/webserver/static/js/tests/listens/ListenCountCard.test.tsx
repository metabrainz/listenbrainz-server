import * as React from "react";
import { mount } from "enzyme";

import ListenCountCard from "../../src/listens/ListenCountCard";

describe("ListenCountCard", () => {
  it("renders correctly when listen count is not zero", () => {
    const wrapper = mount(<ListenCountCard listenCount={100} />);
    expect(wrapper).toMatchSnapshot();
  });
  it("renders correctly when listen count is zero or undefined", () => {
    const wrapper = mount(<ListenCountCard />);
    expect(wrapper).toMatchSnapshot();
  });
});
