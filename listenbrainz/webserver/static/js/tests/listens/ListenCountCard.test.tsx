import * as React from "react";
import { mount } from "enzyme";

import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import ListenCountCard from "../../src/listens/ListenCountCard";
import APIService from "../../src/utils/APIService";

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
  currentUser: loggedInUser,
};

describe("ListenCountCard", () => {
  it("renders correctly when listen count is not zero", () => {
    const wrapper = mount(<ListenCountCard user={user} listenCount={100} />);
    expect(wrapper).toMatchSnapshot();
  });
  it("renders correctly when listen count is zero or undefined", () => {
    const wrapper = mount(<ListenCountCard user={user} />);
    expect(wrapper).toMatchSnapshot();
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
      '<div>track_listener has listened to<hr>100<br><small class="text-muted">songs so far</small></div>'
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
      '<div>You have listened to<hr>100<br><small class="text-muted">songs so far</small></div>'
    );
  });
});
