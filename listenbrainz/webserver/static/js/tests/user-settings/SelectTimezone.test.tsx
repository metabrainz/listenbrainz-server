import * as React from "react";
import { mount, ReactWrapper } from "enzyme";
import APIServiceClass from "../../src/utils/APIService";
import GlobalAppContext from "../../src/utils/GlobalAppContext";

import SelectTimezone from "../../src/user-settings/SelectTimezone";

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
        <SelectTimezone {...props} />
      </GlobalAppContext.Provider>
    );

    const instance = wrapper.instance();

    // set valid selectZone state 
    instance.setState({
      selectZone: 'America/Denver',
    });

    const spy = jest.fn();
    instance.context.APIService.resetUserTimezone = spy;

    await instance.submitTimezone();

    expect(spy).toHaveBeenCalledWith( "auth_token",  "America/Denver");

    // test that state was updated
    expect(wrapper.state("userTimezone")).toEqual(
      'America/Denver'
    );
    
  });

  it("calls newAlert", async () => { 
    const wrapper = mount<SelectTimezone>( 
      <SelectTimezone {...{ ...props, newAlert: jest.fn() }} /> 
    ); 
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