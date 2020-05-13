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
    const instance = wrapper.instance();

    instance.maxListens = 385;
    wrapper.setState({ data: userArtistsProcessDataOutput });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });
});

describe("componentDidMount", () => {
  it("extracts current page from the URL if present", () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    delete window.location;
    window.location = {
      href: "https://foobar/user/bazfoo/artists?page=3",
    } as Window["location"];
    instance.componentDidMount();

    expect(instance.currPage).toBe(3);
  });

  it("sets maxListens and totalPages correctly", async () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserStats");
    spy.mockImplementation(() => {
      return Promise.resolve(userArtistsResponse as UserArtistsResponse);
    });

    await instance.componentDidMount();
    expect(spy).toHaveBeenCalledWith("dummyUser", undefined, undefined, 1);
    expect(instance.maxListens).toBe(385);
    expect(instance.totalPages).toBe(7);
  });

  it("calls handlePageChange", async () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    instance.handlePageChange = jest.fn();
    const spy = jest.spyOn(instance.APIService, "getUserStats");
    spy.mockImplementation(() => {
      return Promise.resolve(userArtistsResponse as UserArtistsResponse);
    });
    delete window.location;
    window.location = {
      href: "https://foobar/user/bazfoo/artists",
    } as Window["location"];
    await instance.componentDidMount();

    expect(instance.handlePageChange).toHaveBeenCalledWith(1);
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
    await instance.getData("dummyUser", 0);

    expect(spy).toHaveBeenCalledWith("dummyUser", undefined, 0, 25);
  });
});

describe("processData", () => {
  it("processes data correctly", () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    expect(
      instance.processData(userArtistsResponse as UserArtistsResponse, 0)
    ).toEqual(userArtistsProcessDataOutput);
  });
});

describe("handlePageChange", () => {
  it("sets state correctly and updates currPage", async () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserStats");
    spy.mockImplementation((): any => {
      return Promise.resolve(userArtistsResponse);
    });
    instance.processData = jest.fn().mockImplementationOnce(() => {
      return userArtistsProcessDataOutput;
    });
    await instance.handlePageChange(1);

    expect(instance.processData).toHaveBeenCalledWith(userArtistsResponse, 0);
    expect(wrapper.state("data")).toEqual(userArtistsProcessDataOutput);
    expect(instance.currPage).toBe(1);
  });
});
