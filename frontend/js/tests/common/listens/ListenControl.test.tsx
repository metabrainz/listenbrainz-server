import * as React from "react";
import { mount } from "enzyme";

import { faHeart } from "@fortawesome/free-solid-svg-icons";
import ListenControl, {
  ListenControlProps,
} from "../../../src/common/listens/ListenControl";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const props: ListenControlProps = {
  title: "foobar",
  text: "foobar",
  icon: faHeart,
};

describe("ListenControl", () => {
  it("renders correctly", () => {
    const wrapper = mount(<ListenControl {...props} />);
    expect(wrapper.find("button")).toHaveLength(1);
  });
});
