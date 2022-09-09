import * as React from "react";
import { mount } from "enzyme";

import Pill, { PillProps } from "../../src/personal-recommendations/Pill";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const mockAction = jest.fn();

const props: PillProps = {
  title: "foobar",
  closeButton: true,
  closeAction: mockAction,
};

describe("Pill", () => {
  it("renders correctly", () => {
    const wrapper = mount(<Pill {...props} />);
    expect(wrapper).toMatchSnapshot();
  });

  it("works when you click", () => {
    const wrapper = mount(<Pill {...props} />);
    wrapper.find("button").at(0).simulate("click");
    expect(mockAction).toHaveBeenCalledTimes(1);
  });
});
