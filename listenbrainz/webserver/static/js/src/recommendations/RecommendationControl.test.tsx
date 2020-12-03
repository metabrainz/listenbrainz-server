import * as React from "react";
import { mount } from "enzyme";

import { faMeh } from "@fortawesome/free-solid-svg-icons";

import { faMeh as faMehRegular } from "@fortawesome/free-regular-svg-icons";
import RecommendationControl, {
  RecommendationControlProps,
} from "./RecommendationControl";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const props: RecommendationControlProps = {
  cssClass: "bad_recommendation",
  action: () => {},
  iconHover: faMeh,
  icon: faMehRegular,
  title: "This is a bad recommendation",
};

describe("RecommendationControl", () => {
  it("renders correctly", () => {
    const wrapper = mount(<RecommendationControl {...props} />);
    expect(wrapper).toMatchSnapshot();
    expect(wrapper.props().cssClass).toEqual("bad_recommendation");
    expect(wrapper.props().title).toEqual("This is a bad recommendation");
    expect(wrapper.props().icon).toEqual(faMehRegular);
    expect(wrapper.props().iconHover).toEqual(faMeh);
  });
});
