import * as React from "react";
import { mount, ReactWrapper } from "enzyme";
import { act } from "react-dom/test-utils";
import APIServiceClass from "../../src/utils/APIService";
import GlobalAppContext from "../../src/utils/GlobalAppContext";

import SelectTimezone, {
  SelectTimezoneProps,
  SelectTimezoneState,
} from "../../src/user-settings/SelectTimezone";
import { waitForComponentToPaint } from "../test-utils";

const user_timezone = "America/New_York";
const pg_timezones: Array<[string, string]> = [
  ["Africa/Adnodjan", "+3:00:00 GMT"],
  ["America/Adak", "-9:00:00 GMT"],
];

const globalProps = {
  APIService: new APIServiceClass(""),
  currentUser: {
    id: 1,
    name: "testuser",
    auth_token: "auth_token",
  },
  spotifyAuth: {},
  youtubeAuth: {},
};

const props = {
  pg_timezones,
  user_timezone,
  newAlert: () => {},
};

describe("User settings", () => {
  describe("submitTimezonePage", () => {
    it("renders correctly", () => {
      const extraProps = { ...props, newAlert: jest.fn() };
      const wrapper = mount<SelectTimezone>(
        <GlobalAppContext.Provider value={globalProps}>
          <SelectTimezone {...extraProps} />
        </GlobalAppContext.Provider>
      );

      expect(wrapper.html()).toMatchSnapshot();
    });
  });

  describe("resetTimezone", () => {
    it("calls API, and sets state + creates a new alert on success", async () => {
      const wrapper = mount<SelectTimezone>(
        <GlobalAppContext.Provider value={globalProps}>
          <SelectTimezone {...{ ...props, newAlert: jest.fn() }} />
        </GlobalAppContext.Provider>
      );
      await waitForComponentToPaint(wrapper);

      const instance = wrapper.instance();
      expect(instance.props.user_timezone).toEqual("America/New_York");
      expect(instance.context.currentUser.name).toEqual("testuser");

      await act(() => {
        // set valid selectZone state
        instance.setState({
          selectZone: "America/Denver",
        });
      });
      await waitForComponentToPaint(wrapper);
      expect(wrapper.state("selectZone")).toEqual("America/Denver");

      const spy = jest
        .spyOn(instance.context.APIService, "resetUserTimezone")
        .mockImplementation(() => Promise.resolve(200));
      await act(async () => {
        await instance.submitTimezone();
      });
      await waitForComponentToPaint(wrapper);

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("auth_token", "America/Denver");

      // test that state is updated and success alert is displayed
      expect(wrapper.state("userTimezone")).toEqual("America/Denver");
      expect(instance.props.newAlert).toHaveBeenCalledTimes(1);
      expect(instance.props.newAlert).toHaveBeenCalledWith(
        "success",
        "Your timezone has been saved.",
        ""
      );
    });

    it("calls newAlert", async () => {
      const wrapper = mount<SelectTimezone>(
        <SelectTimezone {...{ ...props, newAlert: jest.fn() }} />
      );
      await waitForComponentToPaint(wrapper);
      const instance = wrapper.instance();

      instance.handleError("error");

      expect(instance.props.newAlert).toHaveBeenCalledTimes(1);
      expect(instance.props.newAlert).toHaveBeenCalledWith(
        "danger",
        "Error",
        "error"
      );
    });
  });
});
