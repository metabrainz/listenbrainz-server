import * as React from "react";
import { mount, ReactWrapper } from "enzyme";
import APIServiceClass from "../../src/utils/APIService";
import GlobalAppContext from "../../src/utils/GlobalAppContext";

import SelectTimezones from "../../src/user-setting/SelectTimezone";

const user_timezone = 'America/New_York'
const pg_timezones:Array<[string, string]> = [['Africa/Adnodjan', '+3:00:00 GMT'],['America/Adak', '-9:00:00 GMT']]

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

describe("submitTimezonePage", () => {
  // const clickButton = (wrapper: ReactWrapper) => {
  //   wrapper.find(".follow-button").at(0).simulate("click");
  // };

  // const mockResetAPICall = (instance: any, status: number) => {
  //   const spy = jest.spyOn(instance.context.APIService, "resetUserTimezone");
  //   spy.mockImplementation(() => Promise.resolve({ status }));
  //   return spy;
  // };

  it("renders correctly", () => {
    const extraProps = { ...props, newAlert: jest.fn() };
    const wrapper = mount<SelectTimezones>(
      <GlobalAppContext.Provider value={globalProps}>
        <SelectTimezones {...extraProps} />
      </GlobalAppContext.Provider>
    );
    expect(wrapper.html()).toMatchSnapshot();
  });
});

describe("resetTimezone", () => {
  it("calls API, and sets state + creates a new alert on success", async () => {
    const extraProps = { ...props, newAlert: jest.fn() };

    const wrapper = mount<SelectTimezones>(
      <GlobalAppContext.Provider value={globalProps}>
        <SelectTimezones {...extraProps} />
      </GlobalAppContext.Provider>
    );

    const instance = wrapper.instance();

    // set valid selectZone state so submit function doesn't fail
    instance.setState({
      selectZone: 'America/Denver',
    });

    // const spy = mockResetAPICall(instance, 200);
    //   clickButton(wrapper);
    //   expect(spy).toHaveBeenCalledTimes(1);
    const spy = jest.fn();
    instance.context.APIService.resetUserTimezone = spy;

    await instance.submitTimezone();

    expect(spy).toHaveBeenCalledWith("testuser", "auth_token", {
      zonename: 'America/Denver'
    });

    expect(instance.props.newAlert).toHaveBeenCalled();

    // test that state was updated
    expect(wrapper.state("success")).toEqual(true);
    expect(wrapper.state("userTimezone")).toEqual(
      'America/Denver'
    );
  });
});