import * as React from "react";
import { mount } from "enzyme";

import NamePill, {
  NamePillProps,
} from "../../src/personal-recommendations/NamePill";
import ListenControl from "../../src/common/listens/ListenControl";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const mockAction = jest.fn();

const props: NamePillProps = {
  title: "foobar",
  closeAction: mockAction,
};

describe("NamePill", () => {
  it("renders correctly", () => {
    const wrapper = mount(<NamePill {...props} />);
    expect(wrapper.find(".pill")).toHaveLength(1);
    expect(wrapper.find(ListenControl)).toHaveLength(1);
  });

  it("works when you click", () => {
    const wrapper = mount(<NamePill {...props} />);
    wrapper.find("button").at(0).simulate("click");
    expect(mockAction).toHaveBeenCalledTimes(1);
  });

  it("renders a close button if closeAction is a function", () => {
    const wrapper = mount(<NamePill title="foobar" closeAction={() => {}} />);
    expect(wrapper.find("button").exists()).toBeTruthy();
  });

  it("does not render a close button if closeAction is not a function (undefined)", () => {
    const wrapper = mount(<NamePill title="foobar" />);
    expect(wrapper.find("button").exists()).toBeFalsy();
  });
});
