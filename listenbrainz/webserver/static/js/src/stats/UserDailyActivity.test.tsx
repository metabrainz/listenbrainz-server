import * as React from "react";
import { mount, shallow } from "enzyme";

import UserDailyActivity, { UserDailyActivityProps } from "./UserDailyActivity";
import APIError from "../APIError";
import * as userDailyActivityResponse from "../__mocks__/userDailyActivity.json";
import * as userDailyActivityProcessedData from "../__mocks__/userDailyActivityProcessData.json";

const props: UserDailyActivityProps = {
  user: {
    name: "foobar",
  },
  range: "week",
  apiUrl: "barfoo",
};

// Set timeZone to UTC+5:30 because the testdata is in that format
// eslint-disable-next-line no-extend-native
Date.prototype.getTimezoneOffset = () => -330;

describe("UserDailyActivity", () => {
  it("renders correctly", () => {
    const wrapper = shallow<UserDailyActivity>(
      <UserDailyActivity {...{ ...props, range: "all_time" }} />
    );

    wrapper.setState({
      data: userDailyActivityProcessedData,
      graphContainerWidth: 1200,
      loading: false,
    });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });

  it("renders corectly when range is invalid", () => {
    const wrapper = mount<UserDailyActivity>(<UserDailyActivity {...props} />);

    wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });
});

describe("componentDidMount", () => {
  it('adds event listener for "resize" event', () => {
    const wrapper = shallow<UserDailyActivity>(
      <UserDailyActivity {...props} />
    );
    const instance = wrapper.instance();

    const spy = jest.spyOn(window, "addEventListener");
    spy.mockImplementationOnce(() => {});
    instance.handleResize = jest.fn();
    instance.componentDidMount();

    expect(spy).toHaveBeenCalledWith("resize", instance.handleResize);
  });

  it('calls "handleResize" once', () => {
    const wrapper = shallow<UserDailyActivity>(
      <UserDailyActivity {...props} />
    );
    const instance = wrapper.instance();

    instance.handleResize = jest.fn();
    instance.componentDidMount();

    expect(instance.handleResize).toHaveBeenCalledTimes(1);
  });
});

describe("componentDidUpdate", () => {
  it("it sets correct state if range is incorrect", () => {
    const wrapper = shallow<UserDailyActivity>(
      <UserDailyActivity {...props} />
    );

    wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
    wrapper.update();

    expect(wrapper.state()).toMatchObject({
      loading: false,
      hasError: true,
      errorMessage: "Invalid range: invalid_range",
    });
  });

  it("calls loadData once if range is valid", () => {
    const wrapper = shallow<UserDailyActivity>(
      <UserDailyActivity {...props} />
    );
    const instance = wrapper.instance();

    instance.loadData = jest.fn();
    wrapper.setProps({ range: "month" });
    wrapper.update();

    expect(instance.loadData).toHaveBeenCalledTimes(1);
  });
});

describe("componentWillUnmount", () => {
  it('removes event listener for "resize" event', () => {
    const wrapper = shallow<UserDailyActivity>(
      <UserDailyActivity {...props} />
    );
    const instance = wrapper.instance();

    const spy = jest.spyOn(window, "removeEventListener");
    spy.mockImplementationOnce(() => {});
    instance.handleResize = jest.fn();
    instance.componentWillUnmount();

    expect(spy).toHaveBeenCalledWith("resize", instance.handleResize);
  });
});

describe("getData", () => {
  it("calls getUserDailyActivity with correct params", async () => {
    const wrapper = shallow<UserDailyActivity>(
      <UserDailyActivity {...props} />
    );
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserDailyActivity");
    spy.mockImplementation(() =>
      Promise.resolve(userDailyActivityResponse as UserDailyActivityResponse)
    );
    const result = await instance.getData();

    expect(spy).toHaveBeenCalledWith("foobar", "week");
    expect(result).toEqual(userDailyActivityResponse);
  });

  it("sets state correctly if data is not calculated", async () => {
    const wrapper = shallow<UserDailyActivity>(
      <UserDailyActivity {...props} />
    );
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserDailyActivity");
    const noContentError = new APIError("NO CONTENT");
    noContentError.response = {
      status: 204,
    } as Response;
    spy.mockImplementation(() => Promise.reject(noContentError));
    await instance.getData();

    expect(wrapper.state()).toMatchObject({
      loading: false,
      hasError: true,
      errorMessage: "Statistics for the user have not been calculated",
    });
  });

  it("throws error", async () => {
    const wrapper = shallow<UserDailyActivity>(
      <UserDailyActivity {...props} />
    );
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserDailyActivity");
    const notFoundError = new APIError("NOT FOUND");
    notFoundError.response = {
      status: 404,
    } as Response;
    spy.mockImplementation(() => Promise.reject(notFoundError));

    await expect(instance.getData()).rejects.toThrow("NOT FOUND");
  });
});

describe("processData", () => {
  it("processes data correctly for all_time", () => {
    const wrapper = shallow<UserDailyActivity>(
      <UserDailyActivity {...{ ...props, range: "all_time" }} />
    );
    const instance = wrapper.instance();

    const result = instance.processData(
      userDailyActivityResponse as UserDailyActivityResponse
    );

    expect(result).toEqual(userDailyActivityProcessedData);
  });
  it("returns an empty array if no payload", () => {
    const wrapper = shallow<UserDailyActivity>(
      <UserDailyActivity {...{ ...props, range: "all_time" }} />
    );
    const instance = wrapper.instance();

    // When stats haven't been calculated, processData is called with an empty object
    const result = instance.processData({} as UserDailyActivityResponse);

    expect(result).toEqual([]);
  });
});

describe("loadData", () => {
  it("calls getData once", async () => {
    const wrapper = shallow<UserDailyActivity>(
      <UserDailyActivity {...props} />
    );
    const instance = wrapper.instance();

    instance.getData = jest.fn();
    instance.processData = jest.fn();
    await instance.loadData();

    expect(instance.getData).toHaveBeenCalledTimes(1);
  });

  it("set state correctly", async () => {
    const wrapper = shallow<UserDailyActivity>(
      <UserDailyActivity {...props} />
    );
    const instance = wrapper.instance();

    instance.getData = jest
      .fn()
      .mockImplementationOnce(() => Promise.resolve(userDailyActivityResponse));
    await instance.loadData();

    expect(wrapper.state()).toMatchObject({
      data: userDailyActivityProcessedData,
      loading: false,
    });
  });
});
