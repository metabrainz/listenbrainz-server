import * as React from "react";
import { mount } from "enzyme";

import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import ListenCountCard from "../../../src/common/listens/ListenCountCard";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";

const user = {
  id: 1,
  name: "track_listener",
};

const loggedInUser = {
  id: 2,
  name: "iliekcomputers",
};

const globalContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  currentUser: loggedInUser,
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIService("foo"),
    { name: "Fnord" }
  ),
};

describe("ListenCountCard", () => {
  it("renders correctly when listen count is not zero", () => {
    const wrapper = mount(<ListenCountCard user={user} listenCount={100} />);
    expect(wrapper.getDOMNode()).toHaveTextContent(
      "track_listener has listened to100songs so far"
    );
  });
  it("renders correctly when listen count is zero or undefined", () => {
    const wrapper = mount(<ListenCountCard user={user} />);
    expect(wrapper.getDOMNode()).toHaveTextContent(
      "track_listener's listens counttrack_listener hasn't listened to any songs yet."
    );
  });
  it("renders user's name instead of 'You' when visiting another user's page", () => {
    const wrapper = mount(
      <GlobalAppContext.Provider value={globalContext}>
        <ListenCountCard user={user} listenCount={100} />
      </GlobalAppContext.Provider>
    );
    const countCard = wrapper.find("#listen-count-card").first().children();
    const cardDiv = countCard.children().first();
    expect(cardDiv.html()).toEqual(
      '<div data-testid="listen-count-card-content">track_listener has listened to<hr>100<br><small class="text-muted">songs so far</small></div>'
    );
  });
  it("renders 'You' when on current user's page", () => {
    const wrapper = mount(
      <GlobalAppContext.Provider value={globalContext}>
        <ListenCountCard user={loggedInUser} listenCount={100} />
      </GlobalAppContext.Provider>
    );
    const countCard = wrapper.find("#listen-count-card").first().children();
    const cardDiv = countCard.children().first();
    expect(cardDiv.html()).toEqual(
      '<div data-testid="listen-count-card-content">You have listened to<hr>100<br><small class="text-muted">songs so far</small></div>'
    );
  });
});
