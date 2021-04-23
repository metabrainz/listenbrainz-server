import * as React from "react";
import { mount, shallow } from "enzyme";

import UserEntityChart from "./UserEntityChart";
import APIError from "../APIError";
import * as userArtistsResponse from "../__mocks__/userArtists.json";
import * as userArtistsProcessDataOutput from "../__mocks__/userArtistsProcessData.json";
import * as userReleasesResponse from "../__mocks__/userReleases.json";
import * as userReleasesProcessDataOutput from "../__mocks__/userReleasesProcessData.json";
import * as userRecordingsResponse from "../__mocks__/userRecordings.json";
import * as userRecordingsProcessDataOutput from "../__mocks__/userRecordingsProcessData.json";

const props = {
  user: {
    id: 0,
    name: "dummyUser",
  },
  apiUrl: "apiUrl",
};

describe("UserEntityChart Page", () => {
  it("renders correctly for artists", () => {
    // We don't need to call componentDidMount during "mount" because we are
    // passing the data manually, so mock the implementation once.
    jest
      .spyOn(UserEntityChart.prototype, "componentDidMount")
      .mockImplementationOnce((): any => {});

    const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />);

    wrapper.setState({
      data: userArtistsProcessDataOutput as UserEntityData,
      startDate: new Date(0),
      endDate: new Date(10),
      maxListens: 70,
    });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly for releases", () => {
    // We don't need to call componentDidMount during "mount" because we are
    // passing the data manually, so mock the implementation once.
    jest
      .spyOn(UserEntityChart.prototype, "componentDidMount")
      .mockImplementationOnce((): any => {});

    const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />);

    wrapper.setState({
      data: userReleasesProcessDataOutput as UserEntityData,
      startDate: new Date(0),
      endDate: new Date(10),
      maxListens: 26,
    });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly for recording", () => {
    // We don't need to call componentDidMount during "mount" because we are
    // passing the data manually, so mock the implementation once.
    jest
      .spyOn(UserEntityChart.prototype, "componentDidMount")
      .mockImplementationOnce((): any => {});

    const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />);

    wrapper.setState({
      data: userRecordingsProcessDataOutput as UserEntityData,
      startDate: new Date(0),
      endDate: new Date(10),
      maxListens: 26,
    });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly if stats are not calculated", () => {
    jest
      .spyOn(UserEntityChart.prototype, "componentDidMount")
      .mockImplementationOnce((): any => {});

    const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />);
    wrapper.setState({
      hasError: true,
      errorMessage: "Statistics for the user have not been calculated",
      entity: "artist",
      range: "all_time",
      currPage: 1,
    });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });
});

describe("componentDidMount", () => {
  it('adds event listener for "popstate" event', () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(window, "addEventListener");
    spy.mockImplementationOnce(() => {});
    instance.syncStateWithURL = jest.fn();
    instance.componentDidMount();

    expect(spy).toHaveBeenCalledWith("popstate", instance.syncStateWithURL);
  });

  it('adds event listener for "resize" event', () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(window, "addEventListener");
    spy.mockImplementationOnce(() => {});
    instance.syncStateWithURL = jest.fn();
    instance.handleResize = jest.fn();
    instance.componentDidMount();

    expect(spy).toHaveBeenCalledWith("resize", instance.handleResize);
  });

  it("calls getURLParams once", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    instance.getURLParams = jest.fn().mockImplementationOnce(() => {
      return { page: 1, range: "all_time", entity: "artist" };
    });
    instance.syncStateWithURL = jest.fn();
    instance.componentDidMount();

    expect(instance.getURLParams).toHaveBeenCalledTimes(1);
  });

  it("calls replaceState with correct parameters", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(window.history, "replaceState");
    spy.mockImplementationOnce(() => {});
    instance.syncStateWithURL = jest.fn();
    instance.componentDidMount();

    expect(spy).toHaveBeenCalledWith(
      null,
      "",
      "?page=1&range=all_time&entity=artist"
    );
  });

  it("calls syncStateWithURL", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    instance.syncStateWithURL = jest.fn();
    instance.componentDidMount();

    expect(instance.syncStateWithURL).toHaveBeenCalledTimes(1);
  });
});

describe("componentWillUnmount", () => {
  it('removes "popstate" event listener', () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(window, "removeEventListener");
    spy.mockImplementationOnce(() => {});
    instance.syncStateWithURL = jest.fn();
    instance.componentWillUnmount();

    expect(spy).toHaveBeenCalledWith("popstate", instance.syncStateWithURL);
  });

  it('removes "resize" event listener', () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(window, "removeEventListener");
    spy.mockImplementationOnce(() => {});
    instance.handleResize = jest.fn();
    instance.componentWillUnmount();

    expect(spy).toHaveBeenCalledWith("resize", instance.handleResize);
  });
});

describe("changePage", () => {
  it("calls setURLParams with correct parameters", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    instance.setURLParams = jest.fn();
    instance.syncStateWithURL = jest.fn();
    instance.changePage(2);

    expect(instance.setURLParams).toHaveBeenCalledWith(2, "", "");
  });

  it("calls syncStateWithURL once", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    instance.setURLParams = jest.fn();
    instance.syncStateWithURL = jest.fn();
    instance.changeRange("week");

    expect(instance.syncStateWithURL).toHaveBeenCalledTimes(1);
  });
});

describe("changeRange", () => {
  it("calls setURLParams with correct parameters", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    instance.setURLParams = jest.fn();
    instance.syncStateWithURL = jest.fn();
    instance.changeRange("week");

    expect(instance.setURLParams).toHaveBeenCalledWith(1, "week", "");
  });

  it("calls syncStateWithURL once", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    instance.setURLParams = jest.fn();
    instance.syncStateWithURL = jest.fn();
    instance.changeRange("week");

    expect(instance.syncStateWithURL).toHaveBeenCalledTimes(1);
  });
});

describe("changeEntity", () => {
  it("calls setURLParams with correct parameters", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    instance.setURLParams = jest.fn();
    instance.syncStateWithURL = jest.fn();
    instance.changeEntity("release");

    expect(instance.setURLParams).toHaveBeenCalledWith(1, "", "release");
  });

  it("calls syncStateWithURL once", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    instance.setURLParams = jest.fn();
    instance.syncStateWithURL = jest.fn();
    instance.changeEntity("release");

    expect(instance.syncStateWithURL).toHaveBeenCalledTimes(1);
  });
});

describe("getInitData", () => {
  it("gets data correctly for artist", async () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserEntity");
    spy.mockImplementation((): any => {
      return Promise.resolve(userArtistsResponse);
    });

    const {
      maxListens,
      totalPages,
      entityCount,
      startDate,
      endDate,
    } = await instance.getInitData("all_time", "artist");

    expect(maxListens).toEqual(70);
    expect(totalPages).toEqual(4);
    expect(entityCount).toEqual(94);
    expect(startDate).toEqual(
      new Date(userArtistsResponse.payload.from_ts * 1000)
    );
    expect(endDate).toEqual(new Date(userArtistsResponse.payload.to_ts * 1000));
  });

  it("gets data correctly for release", async () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserEntity");
    spy.mockImplementation((): any => {
      return Promise.resolve(userReleasesResponse);
    });

    const {
      maxListens,
      totalPages,
      entityCount,
      startDate,
      endDate,
    } = await instance.getInitData("all_time", "release");

    expect(maxListens).toEqual(26);
    expect(totalPages).toEqual(7);
    expect(entityCount).toEqual(164);
    expect(startDate).toEqual(
      new Date(userReleasesResponse.payload.from_ts * 1000)
    );
    expect(endDate).toEqual(
      new Date(userReleasesResponse.payload.to_ts * 1000)
    );
  });

  it("gets data correctly for recording", async () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getUserEntity");
    spy.mockImplementation((): any => {
      return Promise.resolve(userRecordingsResponse);
    });

    const {
      maxListens,
      totalPages,
      entityCount,
      startDate,
      endDate,
    } = await instance.getInitData("all_time", "recording");

    expect(maxListens).toEqual(25);
    expect(totalPages).toEqual(10);
    expect(entityCount).toEqual(227);
    expect(startDate).toEqual(
      new Date(userRecordingsResponse.payload.from_ts * 1000)
    );
    expect(endDate).toEqual(
      new Date(userRecordingsResponse.payload.to_ts * 1000)
    );
  });
});

describe("getData", () => {
  it("calls getUserEntity with correct parameters", async () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
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
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({ entity: "artist" });

    expect(
      instance.processData(userArtistsResponse as UserArtistsResponse, 1)
    ).toEqual(userArtistsProcessDataOutput);
  });

  it("processes data correctly for top releases", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({ entity: "release" });

    expect(
      instance.processData(userReleasesResponse as UserReleasesResponse, 1)
    ).toEqual(userReleasesProcessDataOutput);
  });

  it("processes data correctly for top recordings", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({ entity: "recording" });

    expect(
      instance.processData(userRecordingsResponse as UserRecordingsResponse, 1)
    ).toEqual(userRecordingsProcessDataOutput);
  });
  it("returns an empty array if no payload", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    // When stats haven't been calculated, processData is called with an empty object
    const result = instance.processData({} as UserRecordingsResponse, 1);

    expect(result).toEqual([]);
  });
});

describe("syncStateWithURL", () => {
  it("sets state correctly", async () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    instance.getURLParams = jest.fn().mockImplementationOnce(() => ({
      page: 1,
      range: "all_time",
      entity: "artist",
    }));
    instance.getInitData = jest.fn().mockImplementationOnce(() =>
      Promise.resolve({
        startDate: new Date(0),
        endDate: new Date(10),
        totalPages: 2,
        maxListens: 100,
        entityCount: 50,
      })
    );
    instance.getData = jest
      .fn()
      .mockImplementationOnce(() => Promise.resolve(userArtistsResponse));
    instance.processData = jest
      .fn()
      .mockImplementationOnce(() => userArtistsProcessDataOutput);
    await instance.syncStateWithURL();

    expect(wrapper.state()).toMatchObject({
      data: userArtistsProcessDataOutput,
      currPage: 1,
      range: "all_time",
      entity: "artist",
      startDate: new Date(0),
      endDate: new Date(10),
      totalPages: 2,
      maxListens: 100,
      entityCount: 50,
      hasError: false,
    });
  });

  it("sets state correctly if stats haven't been calculated", async () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();
    instance.getInitData = jest.fn().mockImplementationOnce(() => {
      const error = new APIError("Not calculated");
      error.response = {
        status: 204,
      } as Response;
      return Promise.reject(error);
    });

    await instance.syncStateWithURL();
    expect(wrapper.state()).toMatchObject({
      currPage: 1,
      range: "all_time",
      entity: "artist",
      loading: false,
      entityCount: 0,
      hasError: true,
      errorMessage: "Statistics for the user have not been calculated",
    });
  });

  it("sets state correctly if range is incorrect", async () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    instance.getURLParams = jest.fn().mockImplementationOnce(() => {
      return { range: "invalid_range", entity: "artist", page: 1 };
    });

    await instance.syncStateWithURL();
    expect(wrapper.state()).toMatchObject({
      currPage: 1,
      range: "invalid_range",
      entity: "artist",
      loading: false,
      hasError: true,
      errorMessage: "Invalid range: invalid_range",
    });
  });

  it("sets state correctly if entity is incorrect", async () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    instance.getURLParams = jest.fn().mockImplementationOnce(() => {
      return { range: "all_time", entity: "invalid_entity", page: 1 };
    });

    await instance.syncStateWithURL();
    expect(wrapper.state()).toMatchObject({
      currPage: 1,
      range: "all_time",
      entity: "invalid_entity",
      loading: false,
      hasError: true,
      errorMessage: "Invalid entity: invalid_entity",
    });
  });

  it("sets state correctly if page is incorrect", async () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    instance.getURLParams = jest.fn().mockImplementationOnce(() => {
      return { range: "all_time", entity: "artist", page: 1.5 };
    });

    await instance.syncStateWithURL();
    expect(wrapper.state()).toMatchObject({
      currPage: 1.5,
      range: "all_time",
      entity: "artist",
      loading: false,
      hasError: true,
      errorMessage: "Invalid page: 1.5",
    });
  });
  it("throws error if fetch fails", async () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    instance.getInitData = jest
      .fn()
      .mockImplementationOnce(() => Promise.reject(Error("failed")));

    await expect(instance.syncStateWithURL()).rejects.toThrowError("failed");
  });
});

describe("getURLParams", () => {
  it("gets default parameters if none are provided in the URL", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    const { page, range, entity } = instance.getURLParams();

    expect(page).toEqual(1);
    expect(range).toEqual("all_time");
    expect(entity).toEqual("artist");
  });

  it("gets parameters if provided in the URL", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    delete window.location;
    window.location = {
      href: "https://foobar.org?page=2&range=week&entity=release",
    } as Window["location"];
    const { page, range, entity } = instance.getURLParams();

    expect(page).toEqual(2);
    expect(range).toEqual("week");
    expect(entity).toEqual("release");
  });
});

describe("setURLParams", () => {
  it("sets URL parameters", () => {
    const wrapper = shallow<UserEntityChart>(<UserEntityChart {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(window.history, "pushState");
    spy.mockImplementationOnce(() => {});

    instance.setURLParams(2, "all_time", "release");
    expect(spy).toHaveBeenCalledWith(
      null,
      "",
      "?page=2&range=all_time&entity=release"
    );
  });
});
