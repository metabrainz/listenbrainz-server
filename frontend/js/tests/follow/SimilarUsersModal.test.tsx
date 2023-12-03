import * as React from "react";
import { mount } from "enzyme";
import SimilarUsersModal from "../../src/follow/SimilarUsersModal";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";

const props = {
  user: { name: "shivam-kapila" },
  List: [{ name: "mr_monkey" }],
  similarUsersList: [{ name: "mr_monkey", similarityScore: 0.567 }],
  loggedInUserFollowsUser: () => true,
  updateFollowingList: () => {},
};
const globalContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  youtubeAuth: {},
  spotifyAuth: {},
  currentUser: {} as ListenBrainzUser,
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIService("foo"),
    { name: "Fnord" }
  ),
};

describe("<SimilarUsersModal />", () => {
  it("renders", () => {
    const wrapper = mount(
      <GlobalAppContext.Provider value={globalContext}>
        <SimilarUsersModal {...props} />
      </GlobalAppContext.Provider>
    );
    expect(wrapper.find(".similar-users-list")).toHaveLength(1);
  });
});
