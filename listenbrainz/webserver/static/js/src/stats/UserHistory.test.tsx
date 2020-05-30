import * as React from "react";
import { mount, shallow } from "enzyme";

import UserHistory from "./UserHistory";
import * as userArtistsResponse from "../__mocks__/userArtists.json";
import * as userArtistsProcessDataOutput from "../__mocks__/userArtistsProcessData.json";
import * as userReleasesResponse from "../__mocks__/userReleases.json";
import * as userReleasesProcessDataOutput from "../__mocks__/userReleasesProcessData.json";

const props = {
  user: {
    id: 0,
    name: "dummyUser",
  },
  apiUrl: "apiUrl",
};

describe("UserHistory Page", () => {
  it("renders", () => {
    // We don't need to call componentDidMount during "mount" because we are
    // passing the data manually, so mock the implementation once.
    jest
      .spyOn(UserHistory.prototype, "componentDidMount")
      .mockImplementationOnce((): any => {});

    const wrapper = mount<UserHistory>(<UserHistory {...props} />);

    wrapper.setState({ data: userArtistsProcessDataOutput, maxListens: 385 });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });
});

describe("componentDidMount", () => {
  it("extracts range from the URL if present", async () => {
    const wrapper = shallow<UserHistory>(<UserHistory {...props} />);
    const instance = wrapper.instance();

    delete window.location;
    window.location = {
      href: "https://foobar/user/bazfoo/artists?range=week",
    } as Window["location"];

    instance.changeRange = jest.fn();
    await instance.componentDidMount();

    expect(instance.changeRange).toHaveBeenCalledWith("week");
  });

  it("extracts page from the URL if present", async () => {
    const wrapper = shallow<UserHistory>(<UserHistory {...props} />);
    const instance = wrapper.instance();

    delete window.location;
    window.location = {
      href: "https://foobar/user/bazfoo/artists?page=3",
    } as Window["location"];
    instance.changeRange = jest.fn();
    instance.changePage = jest.fn();
    await instance.componentDidMount();

    expect(instance.changePage).toHaveBeenCalledWith(3);
  });

  it("extracts entity from the URL if present", async () => {
    const wrapper = shallow<UserHistory>(<UserHistory {...props} />);
    const instance = wrapper.instance();

    delete window.location;
    window.location = {
      href: "https://foobar/user/bazfoo/artists?entity=release",
    } as Window["location"];
    instance.changeRange = jest.fn();
    instance.changePage = jest.fn();
    await instance.componentDidMount();

    expect(wrapper.state("entity")).toEqual("release");
  });
});

describe("getData", () => {
  it("calls getUserHistory with correct parameters", async () => {
    const wrapper = shallow<UserHistory>(<UserHistory {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserEntity");
    spy.mockImplementation((): any => {
      return Promise.resolve(userArtistsResponse);
    });
    await instance.getData(2, "all_time", "release");

    expect(spy).toHaveBeenCalledWith(
      "dummyUser",
      "release",
      "all_time",
      25,
      25
    );
  });
});

describe("processData", () => {
  it("processes data correctly for top artists", () => {
    const wrapper = shallow<UserHistory>(<UserHistory {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({ entity: "artist" });

    expect(
      instance.processData(userArtistsResponse as UserArtistsResponse, 1)
    ).toEqual(userArtistsProcessDataOutput);
  });

  it("processes data correctly for top releases", () => {
    const wrapper = shallow<UserHistory>(<UserHistory {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({ entity: "release" });

    expect(
      instance.processData(userReleasesResponse as UserReleasesResponse, 1)
    ).toEqual(userReleasesProcessDataOutput);
  });
});

describe("changePage", () => {
  it("sets state correctly", async () => {
    const wrapper = shallow<UserHistory>(<UserHistory {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserEntity");
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
  it("sets state correctly for artists", async () => {
    const wrapper = shallow<UserHistory>(<UserHistory {...props} />);
    const instance = wrapper.instance();

    instance.getData = jest.fn().mockImplementationOnce(() => {
      return Promise.resolve(userArtistsResponse);
    });
    const spy = jest.spyOn(instance.APIService, "getUserEntity");
    spy.mockImplementation((): any => {
      return Promise.resolve(userArtistsResponse);
    });
    instance.processData = jest.fn().mockImplementationOnce(() => {
      return userArtistsProcessDataOutput;
    });
    wrapper.setState({ entity: "artist" });
    await instance.changeRange("all_time");

    expect(instance.processData).toHaveBeenCalledWith(userArtistsResponse, 1);
    expect(wrapper.state("data")).toEqual(userArtistsProcessDataOutput);
    expect(wrapper.state("range")).toEqual("all_time");
    expect(wrapper.state("currPage")).toEqual(1);
    expect(wrapper.state("startDate")).toEqual(
      new Date(userArtistsResponse.payload.from_ts * 1000)
    );
    expect(wrapper.state("totalPages")).toBe(7);
    expect(wrapper.state("maxListens")).toBe(385);
    expect(wrapper.state("entityCount")).toBe(175);
  });

  it("sets state correctly for releases", async () => {
    const wrapper = shallow<UserHistory>(<UserHistory {...props} />);
    const instance = wrapper.instance();

    instance.getData = jest.fn().mockImplementationOnce(() => {
      return Promise.resolve(userReleasesResponse);
    });
    const spy = jest.spyOn(instance.APIService, "getUserEntity");
    spy.mockImplementation((): any => {
      return Promise.resolve(userReleasesResponse);
    });
    instance.processData = jest.fn().mockImplementationOnce(() => {
      return userReleasesProcessDataOutput;
    });
    wrapper.setState({ entity: "release" });
    await instance.changeRange("all_time");

    expect(instance.processData).toHaveBeenCalledWith(userReleasesResponse, 1);
    expect(wrapper.state("data")).toEqual(userReleasesProcessDataOutput);
    expect(wrapper.state("range")).toEqual("all_time");
    expect(wrapper.state("currPage")).toEqual(1);
    expect(wrapper.state("startDate")).toEqual(
      new Date(userReleasesResponse.payload.from_ts * 1000)
    );
    expect(wrapper.state("totalPages")).toBe(7);
    expect(wrapper.state("maxListens")).toBe(26);
    expect(wrapper.state("entityCount")).toBe(165);
  });
});

describe("changeEntity", () => {
  it("sets state correctly for artists", async () => {
    const wrapper = shallow<UserHistory>(<UserHistory {...props} />);
    const instance = wrapper.instance();

    instance.getData = jest.fn().mockImplementationOnce(() => {
      return Promise.resolve(userArtistsResponse);
    });
    const spy = jest.spyOn(instance.APIService, "getUserEntity");
    spy.mockImplementation((): any => {
      return Promise.resolve(userArtistsResponse);
    });
    instance.processData = jest.fn().mockImplementationOnce(() => {
      return userArtistsProcessDataOutput;
    });
    wrapper.setState({ range: "all_time" });
    await instance.changeEntity("artist");

    expect(instance.processData).toHaveBeenCalledWith(
      userArtistsResponse,
      1,
      "artist"
    );
    expect(wrapper.state("data")).toEqual(userArtistsProcessDataOutput);
    expect(wrapper.state("entity")).toEqual("artist");
    expect(wrapper.state("currPage")).toEqual(1);
    expect(wrapper.state("startDate")).toEqual(
      new Date(userArtistsResponse.payload.from_ts * 1000)
    );
    expect(wrapper.state("totalPages")).toBe(7);
    expect(wrapper.state("maxListens")).toBe(385);
    expect(wrapper.state("entityCount")).toBe(175);
  });

  it("sets state correctly for releases", async () => {
    const wrapper = shallow<UserHistory>(<UserHistory {...props} />);
    const instance = wrapper.instance();

    instance.getData = jest.fn().mockImplementationOnce(() => {
      return Promise.resolve(userReleasesResponse);
    });
    const spy = jest.spyOn(instance.APIService, "getUserEntity");
    spy.mockImplementation((): any => {
      return Promise.resolve(userReleasesResponse);
    });
    instance.processData = jest.fn().mockImplementationOnce(() => {
      return userReleasesProcessDataOutput;
    });
    wrapper.setState({ range: "all_time" });
    await instance.changeEntity("release");

    expect(instance.processData).toHaveBeenCalledWith(
      userReleasesResponse,
      1,
      "release"
    );
    expect(wrapper.state("data")).toEqual(userReleasesProcessDataOutput);
    expect(wrapper.state("entity")).toEqual("release");
    expect(wrapper.state("currPage")).toEqual(1);
    expect(wrapper.state("startDate")).toEqual(
      new Date(userReleasesResponse.payload.from_ts * 1000)
    );
    expect(wrapper.state("totalPages")).toBe(7);
    expect(wrapper.state("maxListens")).toBe(26);
    expect(wrapper.state("entityCount")).toBe(165);
  });
});
