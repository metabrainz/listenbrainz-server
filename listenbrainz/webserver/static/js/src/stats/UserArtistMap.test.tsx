import * as React from "react";
import { mount, shallow } from "enzyme";

import UserArtistMap, { UserArtistMapProps } from "./UserArtistMap";
import APIError from "../APIError";
import * as userArtistMapResponse from "../__mocks__/userArtistMap.json";
import * as userArtistMapProcessedDataArtist from "../__mocks__/userArtistMapProcessDataArtist.json";
import * as userArtistMapProcessedDataListen from "../__mocks__/userArtistMapProcessDataListen.json";

const props: UserArtistMapProps = {
  user: {
    name: "foobar",
  },
  range: "week",
  apiUrl: "barfoo",
};

describe("UserArtistMap", () => {
  it("renders correctly", () => {
    const wrapper = shallow<UserArtistMap>(
      <UserArtistMap {...{ ...props, range: "all_time" }} />
    );

    wrapper.setState({
      countOf: "artist",
      data: userArtistMapProcessedDataArtist,
      graphContainerWidth: 1200,
      loading: false,
    });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });

  it("renders corectly when range is invalid", () => {
    const wrapper = mount<UserArtistMap>(<UserArtistMap {...props} />);

    wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });
});

describe("componentDidMount", () => {
  it('adds event listener for "resize" event', () => {
    const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(window, "addEventListener");
    spy.mockImplementationOnce(() => {});
    instance.handleResize = jest.fn();
    instance.componentDidMount();

    expect(spy).toHaveBeenCalledWith("resize", instance.handleResize);
  });

  it('calls "handleResize" once', () => {
    const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
    const instance = wrapper.instance();

    instance.handleResize = jest.fn();
    instance.componentDidMount();

    expect(instance.handleResize).toHaveBeenCalledTimes(1);
  });
});

describe("componentDidUpdate", () => {
  it("it sets correct state if range is incorrect", () => {
    const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);

    wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
    wrapper.update();

    expect(wrapper.state()).toMatchObject({
      loading: false,
      hasError: true,
      errorMessage: "Invalid range: invalid_range",
    });
  });

  it("calls loadData once if range is valid", () => {
    const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
    const instance = wrapper.instance();

    instance.loadData = jest.fn();
    wrapper.setProps({ range: "month" });
    wrapper.update();

    expect(instance.loadData).toHaveBeenCalledTimes(1);
  });
});

describe("componentWillUnmount", () => {
  it('removes event listener for "resize" event', () => {
    const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(window, "removeEventListener");
    spy.mockImplementationOnce(() => {});
    instance.handleResize = jest.fn();
    instance.componentWillUnmount();

    expect(spy).toHaveBeenCalledWith("resize", instance.handleResize);
  });
});

describe("getData", () => {
  it("calls getUserArtistMap with correct params", async () => {
    const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserArtistMap");
    spy.mockImplementation(() =>
      Promise.resolve(userArtistMapResponse as UserArtistMapResponse)
    );
    const result = await instance.getData();

    expect(spy).toHaveBeenCalledWith("foobar", "week");
    expect(result).toEqual(userArtistMapResponse);
  });

  it("sets state correctly if data is not calculated", async () => {
    const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserArtistMap");
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
    const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserArtistMap");
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
    const wrapper = shallow<UserArtistMap>(
      <UserArtistMap {...{ ...props, range: "all_time" }} />
    );
    const instance = wrapper.instance();

    const result = instance.processData(
      userArtistMapResponse as UserArtistMapResponse,
      "artist"
    );

    expect(result).toEqual(userArtistMapProcessedDataArtist);
  });

  it("processes data correctly for listen", () => {
    const wrapper = shallow<UserArtistMap>(
      <UserArtistMap {...{ ...props, range: "all_time" }} />
    );
    const instance = wrapper.instance();

    const result = instance.processData(
      userArtistMapResponse as UserArtistMapResponse,
      "listen"
    );

    expect(result).toEqual(userArtistMapProcessedDataListen);
  });
});

describe("changeCountOf", () => {
  it('sets state correctly for "artist"', () => {
    const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
    const instance = wrapper.instance();

    instance.rawData = userArtistMapResponse as UserArtistMapResponse;

    instance.changeCountOf("artist");
    expect(wrapper.state()).toMatchObject({
      data: userArtistMapProcessedDataArtist,
      countOf: "artist",
    });
  });

  it('sets state correctly for "listen"', () => {
    const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
    const instance = wrapper.instance();

    instance.rawData = userArtistMapResponse as UserArtistMapResponse;

    instance.changeCountOf("listen");
    expect(wrapper.state()).toMatchObject({
      data: userArtistMapProcessedDataListen,
      countOf: "listen",
    });
  });
});

describe("loadData", () => {
  it("calls getData once", async () => {
    const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
    const instance = wrapper.instance();

    instance.getData = jest.fn();
    instance.processData = jest.fn();
    await instance.loadData();

    expect(instance.getData).toHaveBeenCalledTimes(1);
  });

  it("set state correctly", async () => {
    const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
    const instance = wrapper.instance();

    instance.getData = jest
      .fn()
      .mockImplementationOnce(() => Promise.resolve(userArtistMapResponse));
    await instance.loadData();

    expect(instance.rawData).toMatchObject(userArtistMapResponse);

    expect(wrapper.state()).toMatchObject({
      data: userArtistMapProcessedDataArtist,
      loading: false,
    });
  });
});
