import * as React from "react";
import { mount } from "enzyme";

import SearchDropDown, {
  SearchDropDownProps,
} from "../../src/personal-recommendations/SearchDropDown";

const mockAction = jest.fn();

const props: SearchDropDownProps = {
  action: mockAction,
  suggestions: ["hrik2001", "riksucks"],
};

describe("<SearchDropDown />", () => {
  beforeAll(() => {
    // Font Awesome generates a random hash ID for each icon everytime.
    // Mocking Math.random() fixes this
    // https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
    jest.spyOn(global.Math, "random").mockImplementation(() => 0);
  });

  it("renders suggestions", () => {
    const wrapper = mount(<SearchDropDown {...props} />);
    expect(wrapper.find("button").at(0).contains("hrik2001")).toBeTruthy();
    expect(wrapper.find("button").at(1).contains("riksucks")).toBeTruthy();
  });

  it("clicks work on suggestions", () => {
    const wrapper = mount(<SearchDropDown {...props} />);
    wrapper.find("button").at(0).simulate("click");
    expect(mockAction).toHaveBeenCalledTimes(1);
  });
});
