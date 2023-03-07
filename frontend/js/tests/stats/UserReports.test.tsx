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
  let wrapper:
    | ShallowWrapper<UserReportsProps, UserReportsState, UserReports>
    | undefined;
  beforeEach(() => {
    wrapper = undefined;
  });
  afterEach(() => {
    if (wrapper) {
      /* Unmount the wrapper at the end of each test, otherwise react-dom throws errors
        related to async lifecycle methods run against a missing dom 'document'.
        See https://github.com/facebook/react/issues/15691
      */
      wrapper.unmount();
    }
  });
  describe("UserReports", () => {
    it("renders without crashing", () => {
      wrapper = shallow<UserReports>(<UserReports {...props} />);

      expect(wrapper).toMatchSnapshot();
    });
  });

  describe("ComponentDidMount", () => {
    it('adds event listener for "popstate" event', () => {
      wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      const spy = jest.spyOn(window, "addEventListener");
      spy.mockImplementationOnce(() => {});
      instance.syncStateWithURL = jest.fn();
      instance.componentDidMount();

      expect(spy).toHaveBeenCalledWith("popstate", instance.syncStateWithURL);
    });

    it("calls getURLParams once", () => {
      wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      instance.getURLParams = jest.fn();
      instance.syncStateWithURL = jest.fn();
      instance.componentDidMount();

      expect(instance.getURLParams).toHaveBeenCalledTimes(1);
    });

    it("calls replaceState with correct parameters", () => {
      wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      const spy = jest.spyOn(window.history, "replaceState");
      spy.mockImplementationOnce(() => {});
      instance.getURLParams = jest.fn().mockImplementationOnce(() => "week");
      instance.syncStateWithURL = jest.fn();
      instance.componentDidMount();

      expect(spy).toHaveBeenCalledWith(null, "", "?range=week");
    });

    it("calls syncStateWithURL", () => {
      wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      instance.syncStateWithURL = jest.fn();
      instance.componentDidMount();

      expect(instance.syncStateWithURL).toHaveBeenCalledTimes(1);
    });
  });

  describe("componentWillUnmount", () => {
    it('removes "popstate" event listener', () => {
      wrapper = shallow<UserReports>(<UserReports {...props} />);
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
      wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      instance.setURLParams = jest.fn();
      instance.syncStateWithURL = jest.fn();
      instance.changeRange("year");

      expect(instance.setURLParams).toHaveBeenCalledWith("year");
    });

    it("calls syncStateWithURL once", () => {
      wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      instance.syncStateWithURL = jest.fn();
      instance.changeRange("year");

      expect(instance.syncStateWithURL).toHaveBeenCalledTimes(1);
    });
  });

  describe("syncStateWithUrl", () => {
    it("calls getURLParams once", () => {
      wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      instance.getURLParams = jest.fn();
      instance.syncStateWithURL();

      expect(instance.getURLParams).toHaveBeenCalledTimes(1);
    });

    it("sets state correcty", () => {
      wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      instance.getURLParams = jest.fn().mockImplementationOnce(() => "month");
      instance.syncStateWithURL();

      expect(wrapper.state("range")).toEqual("month");
    });
  });

  describe("getURLParams", () => {
    it("gets default parameters if none are provided in the URL", () => {
      wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      window.location = {
        href: "https://foobar.org",
      } as Window["location"];
      const range = instance.getURLParams();

      expect(range).toEqual("week");
    });

    it("gets parameters if provided in the URL", () => {
      wrapper = shallow<UserReports>(<UserReports {...props} />);
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
      wrapper = shallow<UserReports>(<UserReports {...props} />);
      const instance = wrapper.instance();

      const spy = jest.spyOn(window.history, "pushState");
      spy.mockImplementationOnce(() => {});

      instance.setURLParams("all_time");
      expect(spy).toHaveBeenCalledWith(null, "", "?range=all_time");
    });
  });
});
