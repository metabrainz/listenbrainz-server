import * as React from "react";
import { mount } from "enzyme";
import SimilarUsersModal from "../../src/follow/SimilarUsersModal";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";

const props = {
  user: { name: "shivam-kapila" },
  List: [{ name: "mr_monkey" }],
  similarUsersList: [{ name: "mr_monkey", similarityScore: 0.567 }],
  loggedInUserFollowsUser: () => true,
  updateFollowingList: () => {},
};
const globalContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  youtubeAuth: {},
  spotifyAuth: {},
  currentUser: {} as ListenBrainzUser,
};

describe("<SimilarUsersModal />", () => {
  it("renders", () => {
    const wrapper = mount(
      <GlobalAppContext.Provider value={globalContext}>
        <SimilarUsersModal {...props} />
      </GlobalAppContext.Provider>
    );
    expect(wrapper.html()).toMatchSnapshot();
  });
});
