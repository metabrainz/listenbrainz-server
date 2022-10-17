import * as React from "react";
import { mount } from "enzyme";

import NamePill, {
  NamePillProps,
} from "../../src/personal-recommendations/NamePill";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const mockAction = jest.fn();

const props: NamePillProps = {
  title: "foobar",
  closeButton: true,
  closeAction: mockAction,
};

describe("NamePill", () => {
  it("renders correctly", () => {
    const wrapper = mount(<NamePill {...props} />);
    expect(wrapper).toMatchSnapshot();
  });

  it("works when you click", () => {
    const wrapper = mount(<NamePill {...props} />);
    wrapper.find("button").at(0).simulate("click");
    expect(mockAction).toHaveBeenCalledTimes(1);
  });

  it("renders according to closeButton", () => {
    const wrapper = mount(
      <NamePill title="foobar" closeButton={false} closeAction={mockAction} />
    );
    expect(wrapper.find("button").exists()).toBeFalsy();
  });
});
