import * as React from "react";
import { mount, ReactWrapper } from "enzyme";

import { act } from "react-dom/test-utils";
import UserEntityChart, {
  UserEntityChartProps,
  UserEntityChartState,
} from "../../src/stats/UserEntityChart";
import APIError from "../../src/utils/APIError";
import APIService from "../../src/utils/APIService";
import * as userArtistsResponse from "../__mocks__/userArtists.json";
import * as userArtistsProcessDataOutput from "../__mocks__/userArtistsProcessData.json";
import * as userReleasesResponse from "../__mocks__/userReleases.json";
import * as userReleasesProcessDataOutput from "../__mocks__/userReleasesProcessData.json";
import * as userRecordingsResponse from "../__mocks__/userRecordings.json";
import * as userRecordingsProcessDataOutput from "../__mocks__/userRecordingsProcessData.json";
import { waitForComponentToPaint } from "../test-utils";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const userProps = {
  user: {
    id: 0,
    name: "dummyUser",
  },
  apiUrl: "apiUrl",
  newAlert: jest.fn(),
};

const sitewideProps = {
  apiUrl: "apiUrl",
  newAlert: jest.fn(),
};

const GlobalContextMock = {
  APIService: new APIService("base-uri"),
  spotifyAuth: {
    access_token: "heyo",
    permission: [
      "user-read-currently-playing",
      "user-read-recently-played",
    ] as Array<SpotifyPermission>,
  },
  youtubeAuth: {
    api_key: "fake-api-key",
  },
  currentUser: { name: "" },
};

describe.each([
  ["User Stats", userProps],
  ["Sitewide Stats", sitewideProps],
])("%s", (name, props) => {
  describe("UserEntityChart Page", () => {
    it("renders correctly for artists", async () => {
      // We don't need to call componentDidMount during "mount" because we are
      // passing the data manually, so mock the implementation once.
      jest
        .spyOn(UserEntityChart.prototype, "componentDidMount")
        .mockImplementationOnce((): any => {});

      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />);
      await act(() => {
        wrapper.setState({
          data: userArtistsProcessDataOutput as UserEntityData,
          startDate: new Date(0),
          endDate: new Date(10),
          maxListens: 70,
        });
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper).toMatchSnapshot();
      wrapper.unmount();
    });

    it("renders correctly for releases", async () => {
      // We don't need to call componentDidMount during "mount" because we are
      // passing the data manually, so mock the implementation once.
      jest
        .spyOn(UserEntityChart.prototype, "componentDidMount")
        .mockImplementationOnce((): any => {});

      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />);

      await act(() => {
        wrapper.setState({
          data: userReleasesProcessDataOutput as UserEntityData,
          startDate: new Date(0),
          endDate: new Date(10),
          maxListens: 26,
        });
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper).toMatchSnapshot();
      wrapper.unmount();
    });

    it("renders correctly for recording", async () => {
      // We don't need to call componentDidMount during "mount" because we are
      // passing the data manually, so mock the implementation once.
      jest
        .spyOn(UserEntityChart.prototype, "componentDidMount")
        .mockImplementationOnce((): any => {});

      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />);

      await act(() => {
        wrapper.setState({
          data: userRecordingsProcessDataOutput as UserEntityData,
          startDate: new Date(0),
          endDate: new Date(10),
          maxListens: 26,
        });
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper).toMatchSnapshot();
      wrapper.unmount();
    });

    it("renders correctly if stats are not calculated", async () => {
      jest
        .spyOn(UserEntityChart.prototype, "componentDidMount")
        .mockImplementationOnce((): any => {});

      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />);
      await act(() => {
        wrapper.setState({
          hasError: true,
          errorMessage: "Statistics for the user have not been calculated",
          entity: "artist",
          range: "all_time",
          currPage: 1,
        });
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper).toMatchSnapshot();
      wrapper.unmount();
    });
  });

  describe("componentDidMount", () => {
    it('adds event listener for "popstate" event', () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      const spy = jest.spyOn(window, "addEventListener");
      spy.mockImplementationOnce(() => {});
      instance.syncStateWithURL = jest.fn();
      act(() => {
        instance.componentDidMount();
      });

      expect(spy).toHaveBeenCalledWith("popstate", instance.syncStateWithURL);
      wrapper.unmount();
    });

    it('adds event listener for "resize" event', () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      const spy = jest.spyOn(window, "addEventListener");
      spy.mockImplementationOnce(() => {});
      instance.syncStateWithURL = jest.fn();
      instance.handleResize = jest.fn();
      act(() => {
        instance.componentDidMount();
      });

      expect(spy).toHaveBeenCalledWith("resize", instance.handleResize);
      wrapper.unmount();
    });

    it("calls getURLParams once", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      instance.getURLParams = jest.fn().mockImplementationOnce(() => {
        return { page: 1, range: "all_time", entity: "artist" };
      });
      instance.syncStateWithURL = jest.fn();
      act(() => {
        instance.componentDidMount();
      });

      expect(instance.getURLParams).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("calls replaceState with correct parameters", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      const spy = jest.spyOn(window.history, "replaceState");
      spy.mockImplementationOnce(() => {});
      instance.syncStateWithURL = jest.fn();
      act(() => {
        instance.componentDidMount();
      });

      expect(spy).toHaveBeenCalledWith(
        null,
        "",
        "?page=1&range=all_time&entity=artist"
      );
      wrapper.unmount();
    });

    it("calls syncStateWithURL", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      instance.syncStateWithURL = jest.fn();
      act(() => {
        instance.componentDidMount();
      });

      expect(instance.syncStateWithURL).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });
  });

  describe("componentWillUnmount", () => {
    it('removes "popstate" event listener', () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      const spy = jest.spyOn(window, "removeEventListener");
      spy.mockImplementationOnce(() => {});
      instance.syncStateWithURL = jest.fn();
      act(() => {
        instance.componentWillUnmount();
      });

      expect(spy).toHaveBeenCalledWith("popstate", instance.syncStateWithURL);
      wrapper.unmount();
    });

    it('removes "resize" event listener', () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      const spy = jest.spyOn(window, "removeEventListener");
      spy.mockImplementationOnce(() => {});
      instance.handleResize = jest.fn();
      act(() => {
        instance.componentWillUnmount();
      });

      expect(spy).toHaveBeenCalledWith("resize", instance.handleResize);
      wrapper.unmount();
    });
  });

  describe("changePage", () => {
    it("calls setURLParams with correct parameters", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      instance.setURLParams = jest.fn();
      instance.syncStateWithURL = jest.fn();

      act(() => {
        instance.changePage(2);
      });

      expect(instance.setURLParams).toHaveBeenCalledWith(2, "", "");
      wrapper.unmount();
    });

    it("calls syncStateWithURL once", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      instance.setURLParams = jest.fn();
      instance.syncStateWithURL = jest.fn();

      act(() => {
        instance.changeRange("week");
      });

      expect(instance.syncStateWithURL).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });
  });

  describe("changeRange", () => {
    it("calls setURLParams with correct parameters", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      instance.setURLParams = jest.fn();
      instance.syncStateWithURL = jest.fn();

      act(() => {
        instance.changeRange("week");
      });

      expect(instance.setURLParams).toHaveBeenCalledWith(1, "week", "");
      wrapper.unmount();
    });

    it("calls syncStateWithURL once", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      instance.setURLParams = jest.fn();
      instance.syncStateWithURL = jest.fn();

      act(() => {
        instance.changeRange("week");
      });

      expect(instance.syncStateWithURL).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });
  });

  describe("changeEntity", () => {
    it("calls setURLParams with correct parameters", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      const setURLParamsSpy = jest.spyOn(instance, "setURLParams");

      act(() => {
        instance.changeEntity("release");
      });

      expect(setURLParamsSpy).toHaveBeenCalledWith(1, "", "release");
      wrapper.unmount();
    });

    it("calls syncStateWithURL once", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      const syncStateWithURLSpy = jest.spyOn(instance, "syncStateWithURL");

      act(() => {
        instance.changeEntity("release");
      });

      expect(syncStateWithURLSpy).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });
  });

  describe("getInitData", () => {
    it("gets data correctly for artist", async () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      const spy = jest.spyOn(instance.context.APIService, "getUserEntity");
      spy.mockImplementation((): any => {
        return Promise.resolve(userArtistsResponse);
      });

      await act(async () => {
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
        expect(endDate).toEqual(
          new Date(userArtistsResponse.payload.to_ts * 1000)
        );
      });
      wrapper.unmount();
    });

    it("gets data correctly for release", async () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      const spy = jest.spyOn(instance.context.APIService, "getUserEntity");
      spy.mockImplementation((): any => {
        return Promise.resolve(userReleasesResponse);
      });
      await act(async () => {
        const {
          maxListens,
          totalPages,
          entityCount,
          startDate,
          endDate,
        } = await instance.getInitData("all_time", "release");

        expect(maxListens).toEqual(57);
        expect(totalPages).toEqual(7);
        expect(entityCount).toEqual(164);
        expect(startDate).toEqual(
          new Date(userReleasesResponse.payload.from_ts * 1000)
        );
        expect(endDate).toEqual(
          new Date(userReleasesResponse.payload.to_ts * 1000)
        );
      });
      wrapper.unmount();
    });

    it("gets data correctly for recording", async () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      const spy = jest.spyOn(instance.context.APIService, "getUserEntity");
      spy.mockImplementation((): any => {
        return Promise.resolve(userRecordingsResponse);
      });
      await act(async () => {
        const {
          maxListens,
          totalPages,
          entityCount,
          startDate,
          endDate,
        } = await instance.getInitData("all_time", "recording");

        expect(maxListens).toEqual(57);
        expect(totalPages).toEqual(10);
        expect(entityCount).toEqual(227);
        expect(startDate).toEqual(
          new Date(userRecordingsResponse.payload.from_ts * 1000)
        );
        expect(endDate).toEqual(
          new Date(userRecordingsResponse.payload.to_ts * 1000)
        );
      });
      wrapper.unmount();
    });
  });

  describe("getData", () => {
    it("calls getUserEntity with correct parameters", async () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      const spy = jest.spyOn(instance.context.APIService, "getUserEntity");
      spy.mockImplementation((): any => {
        return Promise.resolve(userArtistsResponse);
      });
      await act(async () => {
        await instance.getData(2, "all_time", "release");
      });

      expect(spy).toHaveBeenCalledWith(
        // @ts-ignore
        props?.user?.name,
        "release",
        "all_time",
        25,
        25
      );
      wrapper.unmount();
    });
  });

  describe("processData", () => {
    it("processes data correctly for top artists", async () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();
      act(() => {
        wrapper.setState({ entity: "artist" });
      });
      await act(async () => {
        const data = instance.processData(
          userArtistsResponse as UserArtistsResponse,
          1
        );
        expect(data).toEqual(userArtistsProcessDataOutput);
      });
      wrapper.unmount();
    });

    it("processes data correctly for top releases", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();
      act(() => {
        wrapper.setState({ entity: "release" });
      });
      act(() => {
        const data = instance.processData(
          userReleasesResponse as UserReleasesResponse,
          1
        );
        expect(data).toEqual(userReleasesProcessDataOutput);
      });
      wrapper.unmount();
    });

    it("processes data correctly for top recordings", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();
      act(() => {
        wrapper.setState({ entity: "recording" });
      });

      act(() => {
        const data = instance.processData(
          userRecordingsResponse as UserRecordingsResponse,
          1
        );
        expect(data).toEqual(userRecordingsProcessDataOutput);
      });
      wrapper.unmount();
    });
    it("returns an empty array if no payload", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      // When stats haven't been calculated, processData is called with an empty object
      act(() => {
        const result = instance.processData({} as UserRecordingsResponse, 1);

        expect(result).toEqual([]);
      });
      wrapper.unmount();
    });
  });

  describe("syncStateWithURL", () => {
    it("sets state correctly", async () => {
      jest
        .spyOn(UserEntityChart.prototype, "componentDidMount")
        .mockImplementationOnce((): any => {});
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();
      await waitForComponentToPaint(wrapper);

      instance.getURLParams = jest.fn().mockReturnValue({
        page: 1,
        range: "all_time",
        entity: "artist",
      });
      jest.spyOn(instance, "getInitData").mockResolvedValue({
        startDate: new Date(0),
        endDate: new Date(10),
        totalPages: 2,
        maxListens: 100,
        entityCount: 50,
      });
      jest
        .spyOn(instance.context.APIService, "getUserEntity")
        .mockResolvedValue(userArtistsResponse as UserArtistsResponse);
      jest
        .spyOn(instance, "processData")
        .mockImplementation(
          () => userArtistsProcessDataOutput as UserEntityData
        );

      await act(async () => {
        await instance.syncStateWithURL();
      });

      expect(instance.state).toMatchObject({
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
      wrapper.unmount();
    });

    it("sets state correctly if stats haven't been calculated", async () => {
      jest
        .spyOn(UserEntityChart.prototype, "componentDidMount")
        .mockImplementationOnce((): any => {});
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();
      instance.getInitData = jest.fn().mockImplementationOnce(() => {
        const error = new APIError("Not calculated");
        error.response = {
          status: 204,
        } as Response;
        return Promise.reject(error);
      });

      await act(async () => {
        await instance.syncStateWithURL();
      });
      expect(instance.state).toMatchObject({
        currPage: 1,
        range: "all_time",
        entity: "artist",
        loading: false,
        entityCount: 0,
        hasError: true,
        errorMessage: "Statistics for the user have not been calculated",
      });
      wrapper.unmount();
    });

    it("sets state correctly if range is incorrect", async () => {
      jest
        .spyOn(UserEntityChart.prototype, "componentDidMount")
        .mockImplementationOnce((): any => {});
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      instance.getURLParams = jest.fn().mockImplementationOnce(() => {
        return { range: "invalid_range", entity: "artist", page: 1 };
      });

      await act(async () => {
        await instance.syncStateWithURL();
      });
      expect(instance.state).toMatchObject({
        currPage: 1,
        range: "invalid_range",
        entity: "artist",
        loading: false,
        hasError: true,
        errorMessage: "Invalid range: invalid_range",
      });
      wrapper.unmount();
    });

    it("sets state correctly if entity is incorrect", async () => {
      jest
        .spyOn(UserEntityChart.prototype, "componentDidMount")
        .mockImplementationOnce((): any => {});
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      instance.getURLParams = jest.fn().mockImplementationOnce(() => {
        return { range: "all_time", entity: "invalid_entity", page: 1 };
      });

      await act(async () => {
        await instance.syncStateWithURL();
      });
      expect(instance.state).toMatchObject({
        currPage: 1,
        range: "all_time",
        entity: "invalid_entity",
        loading: false,
        hasError: true,
        errorMessage: "Invalid entity: invalid_entity",
      });
      wrapper.unmount();
    });

    it("sets state correctly if page is incorrect", async () => {
      jest
        .spyOn(UserEntityChart.prototype, "componentDidMount")
        .mockImplementationOnce((): any => {});
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      instance.getURLParams = jest.fn().mockImplementationOnce(() => {
        return { range: "all_time", entity: "artist", page: 1.5 };
      });

      await act(async () => {
        await instance.syncStateWithURL();
      });
      expect(instance.state).toMatchObject({
        currPage: 1.5,
        range: "all_time",
        entity: "artist",
        loading: false,
        hasError: true,
        errorMessage: "Invalid page: 1.5",
      });
      wrapper.unmount();
    });
    it("throws error if fetch fails", async () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();
      const mockError = Error("failed");
      instance.getInitData = jest
        .fn()
        .mockImplementationOnce(() => Promise.reject(mockError));
      const spy = jest.spyOn(console, "error");
      await act(async () => {
        await instance.syncStateWithURL();
      });
      expect(spy).toHaveBeenCalledWith(mockError);
      wrapper.unmount();
    });
  });

  describe("getURLParams", () => {
    it("gets default parameters if none are provided in the URL", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      const { page, range, entity } = instance.getURLParams();

      expect(page).toEqual(1);
      expect(range).toEqual("all_time");
      expect(entity).toEqual("artist");
      wrapper.unmount();
    });

    it("gets parameters if provided in the URL", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      window.location = {
        href: "https://foobar.org?page=2&range=week&entity=release",
      } as Window["location"];
      const { page, range, entity } = instance.getURLParams();

      expect(page).toEqual(2);
      expect(range).toEqual("week");
      expect(entity).toEqual("release");
      wrapper.unmount();
    });
  });

  describe("setURLParams", () => {
    it("sets URL parameters", () => {
      const wrapper = mount<UserEntityChart>(<UserEntityChart {...props} />, {
        context: GlobalContextMock,
      });
      const instance = wrapper.instance();

      const spy = jest.spyOn(window.history, "pushState");
      spy.mockImplementationOnce(() => {});

      instance.setURLParams(2, "all_time", "release");
      expect(spy).toHaveBeenCalledWith(
        null,
        "",
        "?page=2&range=all_time&entity=release"
      );
      wrapper.unmount();
    });
  });
});
