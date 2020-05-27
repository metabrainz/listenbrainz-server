import * as React from "react";
import { mount, shallow } from "enzyme";

import UserArtists from "./UserArtists";
import * as userArtistsResponse from "../__mocks__/userArtists.json";
import * as userArtistsProcessDataOutput from "../__mocks__/userArtistsProcessData.json";

const props = {
  user: {
    id: 0,
    name: "dummyUser",
  },
  apiUrl: "apiUrl",
};

describe("User Artists Page", () => {
  it("renders", () => {
    // We don't need to call componentDidMount during "mount" because we are
    // passing the data manually, so mock the implementation once.
    jest
      .spyOn(UserArtists.prototype, "componentDidMount")
      .mockImplementationOnce((): any => {});

    const wrapper = mount<UserArtists>(<UserArtists {...props} />);

    wrapper.setState({ data: userArtistsProcessDataOutput, maxListens: 385 });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });
});

describe("componentDidMount", () => {
  it("extracts range from the URL if present", () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    delete window.location;
    window.location = {
      href: "https://foobar/user/bazfoo/artists?range=week",
    } as Window["location"];

    instance.changeRange = jest.fn();
    instance.componentDidMount();

    expect(instance.changeRange).toHaveBeenCalledWith("week");
  });

  it("extracts current page from the URL if present", () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    delete window.location;
    window.location = {
      href: "https://foobar/user/bazfoo/artists?page=3",
    } as Window["location"];
    instance.changePage = jest.fn();
    instance.componentDidMount();

    expect(instance.changePage).toHaveBeenCalledWith(3);
  });
});

describe("getData", () => {
  it("calls getUserStats with correct parameters", async () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserStats");
    spy.mockImplementation((): any => {
      return Promise.resolve(userArtistsResponse);
    });
    await instance.getData(2, "all_time");

    expect(spy).toHaveBeenCalledWith("dummyUser", "all_time", 25, 25);
  });
});

describe("processData", () => {
  it("processes data correctly", () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    expect(
      instance.processData(userArtistsResponse as UserArtistsResponse, 1)
    ).toEqual(userArtistsProcessDataOutput);
  });
});

describe("changePage", () => {
  it("sets state correctly", async () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserStats");
    spy.mockImplementation((): any => {
      return Promise.resolve(userArtistsResponse);
    });
    instance.processData = jest.fn().mockImplementationOnce(() => {
      return userArtistsProcessDataOutput;
    });
    await instance.changePage(2);

    expect(instance.processData).toHaveBeenCalledWith(userArtistsResponse, 2);
    expect(wrapper.state("data")).toEqual(userArtistsProcessDataOutput);
    expect(wrapper.state("currPage")).toBe(2);
  });
});

describe("changeRange", () => {
  it("sets state correctly", async () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserStats");
    spy.mockImplementation((): any => {
      return Promise.resolve(userArtistsResponse);
    });
    instance.processData = jest.fn().mockImplementationOnce(() => {
      return userArtistsProcessDataOutput;
    });
    await instance.changeRange("all_time");

    expect(instance.processData).toHaveBeenCalledWith(userArtistsResponse, 1);
    expect(wrapper.state("data")).toEqual(userArtistsProcessDataOutput);
    expect(wrapper.state("range")).toEqual("all_time");
    expect(wrapper.state("currPage")).toEqual(1);
    expect(wrapper.state("totalPages")).toBe(7);
    expect(wrapper.state("maxListens")).toBe(385);
    expect(wrapper.state("artistCount")).toBe(175);
  });
});
