import * as React from "react";
import { shallow } from "enzyme";
import SimilarUsersModal from "./SimilarUsersModal";

const props = {
  user: { name: "shivam-kapila" },
  loggedInUser: null,
  List: [{ name: "mr_monkey" }],
  similarUsersList: [{ name: "mr_monkey", similarityScore: 0.567 }],
  loggedInUserFollowsUser: () => true,
  updateFollowingList: () => {},
};

describe("<SimilarUsersModal />", () => {
  it("renders", () => {
    const wrapper = shallow(<SimilarUsersModal {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
  });
});
