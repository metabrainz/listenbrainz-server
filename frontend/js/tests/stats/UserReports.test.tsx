import * as React from "react";
import { shallow, ShallowWrapper } from "enzyme";

import UserReports, {
  UserReportsProps,
  UserReportsState,
} from "../../src/stats/UserReports";

const userProps: UserReportsProps = {
  user: {
    name: "test_user",
  },
  apiUrl: "foobar",
  newAlert: (): any => {},
};

const sitewideProps: UserReportsProps = {
  apiUrl: "foobar",
  newAlert: (): any => {},
};

describe.each([
  ["User Stats", userProps],
  ["Sitewide Stats", sitewideProps],
])("%s", (name, props) => {
  describe("UserReports", () => {
    it("renders without crashing", () => {
      const wrapper = shallow<UserReports>(<UserReports {...props} />);

      expect(wrapper).toMatchSnapshot();
    });
  });

  describe("ComponentDidMount", () => {
    it('adds event listener for "popstate" event', () => {
      const wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      const spy = jest.spyOn(window, "addEventListener");
      spy.mockImplementationOnce(() => {});
      instance.syncStateWithURL = jest.fn();
      instance.componentDidMount();

      expect(spy).toHaveBeenCalledWith("popstate", instance.syncStateWithURL);
    });

    it("calls getURLParams once", () => {
      const wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      instance.getURLParams = jest.fn();
      instance.syncStateWithURL = jest.fn();
      instance.componentDidMount();

      expect(instance.getURLParams).toHaveBeenCalledTimes(1);
    });

    it("calls replaceState with correct parameters", () => {
      const wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      const spy = jest.spyOn(window.history, "replaceState");
      spy.mockImplementationOnce(() => {});
      instance.getURLParams = jest.fn().mockImplementationOnce(() => "week");
      instance.syncStateWithURL = jest.fn();
      instance.componentDidMount();

      expect(spy).toHaveBeenCalledWith(null, "", "?range=week");
    });

    it("calls syncStateWithURL", () => {
      const wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      instance.syncStateWithURL = jest.fn();
      instance.componentDidMount();

      expect(instance.syncStateWithURL).toHaveBeenCalledTimes(1);
    });
  });

  describe("componentWillUnmount", () => {
    it('removes "popstate" event listener', () => {
      const wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      const spy = jest.spyOn(window, "removeEventListener");
      spy.mockImplementationOnce(() => {});
      instance.syncStateWithURL = jest.fn();
      instance.componentWillUnmount();

      expect(spy).toHaveBeenCalledWith("popstate", instance.syncStateWithURL);
    });
  });

  describe("changeRange", () => {
    it("calls setURLParams with correct parameters", () => {
      const wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      instance.setURLParams = jest.fn();
      instance.syncStateWithURL = jest.fn();
      instance.changeRange("year");

      expect(instance.setURLParams).toHaveBeenCalledWith("year");
    });

    it("calls syncStateWithURL once", () => {
      const wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      instance.syncStateWithURL = jest.fn();
      instance.changeRange("year");

      expect(instance.syncStateWithURL).toHaveBeenCalledTimes(1);
    });
  });

  describe("syncStateWithUrl", () => {
    it("calls getURLParams once", () => {
      const wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      instance.getURLParams = jest.fn();
      instance.syncStateWithURL();

      expect(instance.getURLParams).toHaveBeenCalledTimes(1);
    });

    it("sets state correcty", () => {
      const wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      instance.getURLParams = jest.fn().mockImplementationOnce(() => "month");
      instance.syncStateWithURL();

      expect(wrapper.state("range")).toEqual("month");
    });
  });

  describe("getURLParams", () => {
    it("gets default parameters if none are provided in the URL", () => {
      const wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      window.location = {
        href: "https://foobar.org",
      } as Window["location"];
      const range = instance.getURLParams();

      expect(range).toEqual("week");
    });

    it("gets parameters if provided in the URL", () => {
      const wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      window.location = {
        href: "https://foobar.org?range=year",
      } as Window["location"];
      const range = instance.getURLParams();

      expect(range).toEqual("year");
    });
  });

  describe("setURLParams", () => {
    it("sets URL parameters", () => {
      const wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      const spy = jest.spyOn(window.history, "pushState");
      spy.mockImplementationOnce(() => {});

      instance.setURLParams("all_time");
      expect(spy).toHaveBeenCalledWith(null, "", "?range=all_time");
    });
  });
});
