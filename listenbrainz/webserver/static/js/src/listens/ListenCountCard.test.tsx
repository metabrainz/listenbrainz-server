import * as React from "react";
import { mount } from "enzyme";

import ListenCountCard, { ListenCountCardProps } from "./ListenCountCard";

const props: ListenCountCardProps = {
  listenCount: 100,
};

describe("ListenCountCard", () => {
  it("renders correctly", () => {
    const wrapper = mount(<ListenCountCard {...props} />);
    expect(wrapper).toMatchSnapshot();
  });
});
