import * as React from "react";
import { ReactWrapper, mount, shallow, ShallowWrapper } from "enzyme";

import { act } from "react-dom/test-utils";
import UserArtistMap, {
  UserArtistMapProps,
  UserArtistMapState,
} from "../../src/stats/UserArtistMap";
import APIError from "../../src/utils/APIError";
import * as userArtistMapResponse from "../__mocks__/userArtistMap.json";
import * as userArtistMapProcessedDataArtist from "../__mocks__/userArtistMapProcessDataArtist.json";
import * as userArtistMapProcessedDataListen from "../__mocks__/userArtistMapProcessDataListen.json";
import { waitForComponentToPaint } from "../test-utils";

const userProps: UserArtistMapProps = {
  user: {
    name: "foobar",
  },
  range: "week",
  apiUrl: "barfoo",
};

const sitewideProps: UserArtistMapProps = {
  range: "week",
  apiUrl: "barfoo",
};

describe.each([
  ["User Stats", userProps],
  ["Sitewide Stats", sitewideProps],
])("%s", (name, props) => {
  describe("UserArtistMap", () => {
    it("renders correctly", async () => {
      const wrapper = shallow<UserArtistMap>(
        <UserArtistMap {...{ ...props, range: "all_time" }} />
      );
      await act(() => {
        wrapper.setState({
          selectedMetric: "artist",
          data: userArtistMapProcessedDataArtist,
          graphContainerWidth: 1200,
          loading: false,
        });
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper).toMatchSnapshot();
    });

    it("renders corectly when range is invalid", async () => {
      const wrapper = mount<UserArtistMap>(<UserArtistMap {...props} />);
      await act(() => {
        wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
      });
      await waitForComponentToPaint(wrapper);

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
    it("it sets correct state if range is incorrect", async () => {
      const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);

      await act(() => {
        wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper.state()).toMatchObject({
        loading: false,
        hasError: true,
        errorMessage: "Invalid range: invalid_range",
      });
    });

    it("calls loadData once if range is valid", async () => {
      const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
      const instance = wrapper.instance();

      instance.loadData = jest.fn();
      await act(() => {
        wrapper.setProps({ range: "month" });
      });
      await waitForComponentToPaint(wrapper);

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

      expect(spy).toHaveBeenCalledWith(props?.user?.name, "week");
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
      await act(async () => {
        await instance.getData();
      });
      await waitForComponentToPaint(wrapper);

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
    it("returns an empty array if no payload", () => {
      const wrapper = shallow<UserArtistMap>(
        <UserArtistMap {...{ ...props, range: "all_time" }} />
      );
      const instance = wrapper.instance();

      // When stats haven't been calculated, processData is called with an empty object
      const result = instance.processData(
        {} as UserArtistMapResponse,
        "listen"
      );

      expect(result).toEqual([]);
    });
  });

  describe("changeSelectedMetric", () => {
    it('sets state correctly for "artist"', async () => {
      const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
      const instance = wrapper.instance();

      instance.rawData = userArtistMapResponse as UserArtistMapResponse;

      await act(async () => {
        instance.changeSelectedMetric("artist");
      });
      await waitForComponentToPaint(wrapper);
      expect(wrapper.state()).toMatchObject({
        data: userArtistMapProcessedDataArtist,
        selectedMetric: "artist",
      });
    });

    it('sets state correctly for "listen"', async () => {
      const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
      const instance = wrapper.instance();

      instance.rawData = userArtistMapResponse as UserArtistMapResponse;

      await act(async () => {
        instance.changeSelectedMetric("listen");
      });
      await waitForComponentToPaint(wrapper);
      expect(wrapper.state()).toMatchObject({
        data: userArtistMapProcessedDataListen,
        selectedMetric: "listen",
      });
    });
  });

  describe("loadData", () => {
    it("calls getData once", async () => {
      const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
      const instance = wrapper.instance();

      const spy = jest.fn();
      instance.getData = spy;
      instance.processData = jest.fn();
      await act(async () => {
        await instance.loadData();
      });
      await waitForComponentToPaint(wrapper);

      expect(spy).toHaveBeenCalledTimes(1);
    });

    it("set state correctly", async () => {
      const wrapper = shallow<UserArtistMap>(<UserArtistMap {...props} />);
      const instance = wrapper.instance();

      instance.getData = jest
        .fn()
        .mockImplementationOnce(() => Promise.resolve(userArtistMapResponse));
      await act(async () => {
        await instance.loadData();
      });
      await waitForComponentToPaint(wrapper);

      expect(instance.rawData).toMatchObject(userArtistMapResponse);

      expect(wrapper.state()).toMatchObject({
        data: userArtistMapProcessedDataArtist,
        loading: false,
      });
    });
  });
});
