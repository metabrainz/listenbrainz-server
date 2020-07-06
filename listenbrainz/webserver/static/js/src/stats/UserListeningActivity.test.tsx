import * as React from "react";
import { mount, shallow } from "enzyme";

import UserListeningActivity, {
  UserListeningActivityProps,
} from "./UserListeningActivity";
import * as userListeningActivityResponseWeek from "../__mocks__/userListeningActivityWeek.json";
import * as userListeningActivityResponseMonth from "../__mocks__/userListeningActivityMonth.json";
import * as userListeningActivityResponseYear from "../__mocks__/userListeningActivityYear.json";
import * as userListeningActivityResponseAllTime from "../__mocks__/userListeningActivityAllTime.json";
import * as userListeningActivityProcessedDataWeek from "../__mocks__/userListeningActivityProcessDataWeek.json";
import * as userListeningActivityProcessedDataMonth from "../__mocks__/userListeningActivityProcessDataMonth.json";
import * as userListeningActivityProcessedDataYear from "../__mocks__/userListeningActivityProcessDataYear.json";
import * as userListeningActivityProcessedDataAllTime from "../__mocks__/userListeningActivityProcessDataAllTime.json";

const props: UserListeningActivityProps = {
  user: {
    name: "foobar",
  },
  range: "week",
  apiUrl: "barfoo",
};

describe("UserListeningActivity", () => {
  it("renders correctly for week", () => {
    const wrapper = mount<UserListeningActivity>(
      <UserListeningActivity {...props} />
    );

    wrapper.setState({
      data: userListeningActivityProcessedDataWeek,
      thisRangePeriod: { start: 1591574400, end: 1592092800 },
      lastRangePeriod: { start: 1590969600, end: 1591488000 },
      totalListens: 70,
      avgListens: 10,
    });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly for month", () => {
    const wrapper = mount<UserListeningActivity>(
      <UserListeningActivity {...{ ...props, range: "month" }} />
    );

    wrapper.setState({
      data: userListeningActivityProcessedDataMonth,
      thisRangePeriod: { start: 1590969600 },
      lastRangePeriod: { start: 1588291200 },
      totalListens: 70,
      avgListens: 10,
    });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly for year", () => {
    const wrapper = mount<UserListeningActivity>(
      <UserListeningActivity {...{ ...props, range: "year" }} />
    );

    wrapper.setState({
      data: userListeningActivityProcessedDataYear,
      thisRangePeriod: { start: 1577836800 },
      lastRangePeriod: { start: 1546300800 },
      totalListens: 70,
      avgListens: 10,
    });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly for all_time", () => {
    const wrapper = mount<UserListeningActivity>(
      <UserListeningActivity {...{ ...props, range: "all_time" }} />
    );

    wrapper.setState({
      data: userListeningActivityProcessedDataAllTime,
      thisRangePeriod: {},
      lastRangePeriod: {},
      totalListens: 70,
      avgListens: 10,
    });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });
});
