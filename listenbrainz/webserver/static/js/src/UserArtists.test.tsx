import * as React from "react";
import { mount, shallow } from "enzyme";

import UserArtists from "./UserArtists";
import * as userArtistsResponse from "./__mocks__/userArtists.json";
import * as userArtistsProcessDataOutput from "./__mocks__/userArtistsProcessData.json";

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

    // eslint-disable-next-line dot-notation
    instance["maxListens"] = 385;
    wrapper.setState({ data: userArtistsProcessDataOutput as any });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });
});

describe("componentDidMount", () => {
  it("set current page to 1 if not provided in URL", () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    delete window.location;
    window.location = {
      href: "https://foobar/user/bazfoo/artists",
    } as any;
    instance.componentDidMount();

    // eslint-disable-next-line dot-notation
    expect(instance["currPage"]).toBe(1);
  });

  it("extracts current page from the URL if present", () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    delete window.location;
    window.location = {
      href: "https://foobar/user/bazfoo/artists?page=3",
    } as any;
    instance.componentDidMount();

    // eslint-disable-next-line dot-notation
    expect(instance["currPage"]).toBe(3);
  });

  it("sets maxListens and totalPages correctly", async () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    // eslint-disable-next-line dot-notation
    const spy = jest.spyOn(instance["APIService"], "getUserStats");
    spy.mockImplementation(() => {
      return Promise.resolve(userArtistsResponse);
    });

    await instance.componentDidMount();
    expect(spy).toHaveBeenCalledWith("dummyUser", undefined, undefined, 1);
    // eslint-disable-next-line dot-notation
    expect(instance["maxListens"]).toBe(385);
    // eslint-disable-next-line dot-notation
    expect(instance["totalPages"]).toBe(7);
  });

  it("calls processData and sets state correctly", async () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    // eslint-disable-next-line dot-notation
    const spy = jest.spyOn(instance["APIService"], "getUserStats");
    spy.mockImplementation(() => {
      return Promise.resolve(userArtistsResponse);
    });
    instance.processData = jest.fn().mockImplementationOnce(() => {
      return userArtistsProcessDataOutput;
    });
    delete window.location;
    window.location = {
      href: "https://foobar/user/bazfoo/artists",
    } as any;
    await instance.componentDidMount();

    expect(spy).toHaveBeenCalledWith("dummyUser", undefined, 0, 25);
    expect(instance.processData).toHaveBeenCalledWith(userArtistsResponse, 0);
    expect(wrapper.state("data")).toEqual(userArtistsProcessDataOutput);
  });
});

describe("processData", () => {
  it("processes data correctly", () => {
    const wrapper = shallow<UserArtists>(<UserArtists {...props} />);
    const instance = wrapper.instance();

    expect(instance.processData(userArtistsResponse, 0)).toEqual(
      userArtistsProcessDataOutput
    );
  });
});
