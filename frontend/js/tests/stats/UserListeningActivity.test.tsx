import * as React from "react";
import { mount, ReactWrapper, shallow, ShallowWrapper } from "enzyme";

import { act } from "react-dom/test-utils";
import UserListeningActivity, {
  UserListeningActivityProps,
  UserListeningActivityState,
} from "../../src/stats/UserListeningActivity";
import APIError from "../../src/utils/APIError";
import * as userListeningActivityResponseWeek from "../__mocks__/userListeningActivityWeek.json";
import * as userListeningActivityResponseMonth from "../__mocks__/userListeningActivityMonth.json";
import * as userListeningActivityResponseYear from "../__mocks__/userListeningActivityYear.json";
import * as userListeningActivityResponseAllTime from "../__mocks__/userListeningActivityAllTime.json";
import * as userListeningActivityProcessedDataWeek from "../__mocks__/userListeningActivityProcessDataWeek.json";
import * as userListeningActivityProcessedDataMonth from "../__mocks__/userListeningActivityProcessDataMonth.json";
import * as userListeningActivityProcessedDataYear from "../__mocks__/userListeningActivityProcessDataYear.json";
import * as userListeningActivityProcessedDataAllTime from "../__mocks__/userListeningActivityProcessDataAllTime.json";
import { waitForComponentToPaint } from "../test-utils";

const userProps: UserListeningActivityProps = {
  user: {
    name: "foobar",
  },
  range: "week",
  apiUrl: "barfoo",
};

const sitewideProps: UserListeningActivityProps = {
  range: "week",
  apiUrl: "barfoo",
};

describe.each([
  ["User Stats", userProps],
  ["Sitewide Stats", sitewideProps],
])("%s", (name, props) => {
  describe("UserListeningActivity", () => {
    it("renders correctly for week", async () => {
      const wrapper = mount<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      await act(async () => {
        wrapper.setState({
          data: userListeningActivityProcessedDataWeek,
          thisRangePeriod: { start: 1591574400, end: 1592092800 },
          lastRangePeriod: { start: 1590969600, end: 1591488000 },
          totalListens: 70,
          avgListens: 10,
        });
      });

      expect(wrapper).toMatchSnapshot();
    });

    it("renders correctly for month", async () => {
      const wrapper = mount<UserListeningActivity>(
        <UserListeningActivity {...{ ...props, range: "month" }} />
      );
      await act(async () => {
        wrapper.setState({
          data: userListeningActivityProcessedDataMonth,
          thisRangePeriod: { start: 1590969600 },
          lastRangePeriod: { start: 1588291200 },
          totalListens: 70,
          avgListens: 10,
        });
      });

      expect(wrapper).toMatchSnapshot();
    });

    it("renders correctly for year", async () => {
      const wrapper = mount<UserListeningActivity>(
        <UserListeningActivity {...{ ...props, range: "year" }} />
      );
      await act(async () => {
        wrapper.setState({
          data: userListeningActivityProcessedDataYear,
          thisRangePeriod: { start: 1577836800 },
          lastRangePeriod: { start: 1546300800 },
          totalListens: 70,
          avgListens: 10,
        });
      });

      expect(wrapper).toMatchSnapshot();
    });

    it("renders correctly for all_time", async () => {
      const wrapper = mount<UserListeningActivity>(
        <UserListeningActivity {...{ ...props, range: "all_time" }} />
      );

      await act(async () => {
        wrapper.setState({
          data: userListeningActivityProcessedDataAllTime,
          thisRangePeriod: {},
          lastRangePeriod: {},
          totalListens: 70,
          avgListens: 10,
        });
      });

      expect(wrapper).toMatchSnapshot();
    });

    it("renders corectly when range is invalid", async () => {
      const wrapper = mount<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      await act(async () => {
        wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper).toMatchSnapshot();
    });
  });

  describe("componentDidUpdate", () => {
    it("it sets correct state if range is incorrect", async () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      await act(async () => {
        wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper.state()).toMatchObject({
        loading: false,
        hasError: true,
        errorMessage: "Invalid range: invalid_range",
      });
    });

    it("calls loadData once if range is valid", async () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      const instance = wrapper.instance();

      instance.loadData = jest.fn();
      await act(async () => {
        wrapper.setProps({ range: "month" });
      });

      expect(instance.loadData).toHaveBeenCalledTimes(1);
    });
  });

  describe("getData", () => {
    it("calls getUserListeningActivity with correct params", async () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      const instance = wrapper.instance();

      const spy = jest.spyOn(instance.APIService, "getUserListeningActivity");
      spy.mockImplementation(() =>
        Promise.resolve(
          userListeningActivityResponseWeek as UserListeningActivityResponse
        )
      );
      await act(async () => {
        await instance.getData();
      });

      expect(spy).toHaveBeenCalledWith(props?.user?.name, "week");
    });

    it("sets state correctly if data is not calculated", async () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      const instance = wrapper.instance();

      const spy = jest.spyOn(instance.APIService, "getUserListeningActivity");
      const noContentError = new APIError("NO CONTENT");
      noContentError.response = {
        status: 204,
      } as Response;
      spy.mockImplementation(() => Promise.reject(noContentError));
      await act(async () => {
        await instance.getData();
      });

      expect(wrapper.state()).toMatchObject({
        loading: false,
        hasError: true,
        errorMessage: "Statistics for the user have not been calculated",
      });
    });

    it("throws error", async () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      const instance = wrapper.instance();

      const spy = jest.spyOn(instance.APIService, "getUserListeningActivity");
      const notFoundError = new APIError("NOT FOUND");
      notFoundError.response = {
        status: 404,
      } as Response;
      spy.mockImplementation(() => Promise.reject(notFoundError));

      await expect(instance.getData()).rejects.toThrow("NOT FOUND");
    });
  });

  describe("getNumberOfDaysInMonth", () => {
    it("calculates correctly for non leap February", () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      const instance = wrapper.instance();

      expect(instance.getNumberOfDaysInMonth(new Date(2019, 1, 1))).toEqual(28);
    });

    it("calculates correctly for leap February", () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      const instance = wrapper.instance();

      expect(instance.getNumberOfDaysInMonth(new Date(2020, 1, 1))).toEqual(29);
    });

    it("calculates correctly for December", () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      const instance = wrapper.instance();

      expect(instance.getNumberOfDaysInMonth(new Date(2020, 11, 1))).toEqual(
        31
      );
    });

    it("calculates correctly for November", () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      const instance = wrapper.instance();

      expect(instance.getNumberOfDaysInMonth(new Date(2020, 10, 1))).toEqual(
        30
      );
    });
  });

  describe("processData", () => {
    it("processes data correctly for week", () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      const instance = wrapper.instance();

      const result = instance.processData(
        userListeningActivityResponseWeek as UserListeningActivityResponse
      );

      expect(result).toEqual(userListeningActivityProcessedDataWeek);
    });

    it("processes data correctly for month", () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...{ ...props, range: "month" }} />
      );
      const instance = wrapper.instance();

      const result = instance.processData(
        userListeningActivityResponseMonth as UserListeningActivityResponse
      );

      expect(result).toEqual(userListeningActivityProcessedDataMonth);
    });

    it("processes data correctly for year", () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...{ ...props, range: "year" }} />
      );
      const instance = wrapper.instance();

      const result = instance.processData(
        userListeningActivityResponseYear as UserListeningActivityResponse
      );

      expect(result).toEqual(userListeningActivityProcessedDataYear);
    });

    it("processes data correctly for all_time", async () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...{ ...props, range: "all_time" }} />
      );
      const instance = wrapper.instance();

      const spy = jest.spyOn(Date.prototype, "getFullYear");
      spy.mockImplementationOnce(() =>
        new Date(
          userListeningActivityResponseAllTime.payload.to_ts * 1000
        ).getFullYear()
      );
      let result;
      await act(async () => {
        result = instance.processData(
          userListeningActivityResponseAllTime as UserListeningActivityResponse
        );
      });

      expect(result).toEqual(userListeningActivityProcessedDataAllTime);
    });
    it("returns an empty array if no payload", async () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...{ ...props, range: "year" }} />
      );
      const instance = wrapper.instance();
      let result;
      await act(async () => {
        // When stats haven't been calculated, processData is called with an empty object
        result = instance.processData({} as UserListeningActivityResponse);
      });

      expect(result).toEqual([]);
    });
  });

  describe("loadData", () => {
    it("calls getData once", async () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      const instance = wrapper.instance();

      instance.getData = jest.fn();
      instance.processData = jest.fn();
      await act(async () => {
        await instance.loadData();
      });

      expect(instance.getData).toHaveBeenCalledTimes(1);
    });

    it("set state correctly", async () => {
      const wrapper = shallow<UserListeningActivity>(
        <UserListeningActivity {...props} />
      );
      const instance = wrapper.instance();

      instance.getData = jest
        .fn()
        .mockImplementationOnce(() =>
          Promise.resolve(userListeningActivityResponseWeek)
        );

      await act(async () => {
        await instance.loadData();
      });

      expect(wrapper.state()).toMatchObject({
        data: userListeningActivityProcessedDataWeek,
        loading: false,
      });
    });
  });
});
