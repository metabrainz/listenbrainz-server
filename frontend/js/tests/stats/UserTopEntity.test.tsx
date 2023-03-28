import * as React from "react";
import { mount, ReactWrapper, shallow, ShallowWrapper } from "enzyme";

import { act } from "react-dom/test-utils";
import APIError from "../../src/utils/APIError";
import UserTopEntity, {
  UserTopEntityProps,
  UserTopEntityState,
} from "../../src/stats/UserTopEntity";
import * as userArtists from "../__mocks__/userArtists.json";
import * as userReleases from "../__mocks__/userReleases.json";
import * as userRecordings from "../__mocks__/userRecordings.json";
import { waitForComponentToPaint } from "../test-utils";

const userProps: UserTopEntityProps = {
  range: "week",
  entity: "artist",
  apiUrl: "foobar",
  terminology: "artist",
  user: {
    name: "test_user",
  },
  newAlert: (): any => {},
};

const sitewideProps: UserTopEntityProps = {
  range: "week",
  entity: "artist",
  apiUrl: "foobar",
  terminology: "artist",
  newAlert: (): any => {},
};

describe.each([
  ["User Stats", userProps],
  ["Sitewide Stats", sitewideProps],
])("%s", (name, props) => {
  describe("UserTopEntity", () => {
    it("renders correctly for artist", async () => {
      const wrapper = mount<UserTopEntity>(<UserTopEntity {...props} />);
      await act(() => {
        wrapper.setState({
          data: userArtists as UserArtistsResponse,
          loading: false,
        });
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper).toMatchSnapshot();
      wrapper.unmount();
    });

    it("renders correctly for release", async () => {
      const wrapper = mount<UserTopEntity>(
        <UserTopEntity {...{ ...props, entity: "release" }} />
      );
      await act(() => {
        wrapper.setState({
          data: userReleases as UserReleasesResponse,
          loading: false,
        });
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper).toMatchSnapshot();
      wrapper.unmount();
    });

    it("renders correctly for recording", async () => {
      const wrapper = mount<UserTopEntity>(
        <UserTopEntity {...{ ...props, entity: "recording" }} />
      );
      await act(() => {
        wrapper.setState({
          data: userRecordings as UserRecordingsResponse,
          loading: false,
        });
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper).toMatchSnapshot();
      wrapper.unmount();
    });

    it("renders corectly when range is invalid", async () => {
      const wrapper = mount<UserTopEntity>(<UserTopEntity {...props} />);
      await act(() => {
        wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
        wrapper.setState({ loading: false });
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper).toMatchSnapshot();
      wrapper.unmount();
    });
  });

  describe("componentDidUpdate", () => {
    it("it sets correct state if range is incorrect", async () => {
      const wrapper = shallow<UserTopEntity>(<UserTopEntity {...props} />);
      await act(() => {
        wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper.state()).toMatchObject({
        loading: false,
        hasError: true,
        errorMessage: "Invalid range: invalid_range",
      });
      wrapper.unmount();
    });

    it("calls loadData once if range is valid", async () => {
      const wrapper = shallow<UserTopEntity>(<UserTopEntity {...props} />);
      const instance = wrapper.instance();

      instance.loadData = jest.fn();
      await act(() => {
        wrapper.setProps({ range: "month" });
      });
      await waitForComponentToPaint(wrapper);

      expect(instance.loadData).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });
  });

  describe("loadData", () => {
    it("calls getData once", async () => {
      const wrapper = shallow<UserTopEntity>(<UserTopEntity {...props} />);
      const instance = wrapper.instance();

      instance.getData = jest
        .fn()
        .mockImplementationOnce(() => Promise.resolve(userArtists));
      await instance.loadData();

      expect(instance.getData).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("set state correctly", async () => {
      const wrapper = shallow<UserTopEntity>(<UserTopEntity {...props} />);
      const instance = wrapper.instance();

      instance.getData = jest
        .fn()
        .mockImplementationOnce(() => Promise.resolve(userArtists));
      await instance.loadData();

      expect(wrapper.state()).toMatchObject({
        data: userArtists,
        loading: false,
      });
      wrapper.unmount();
    });
  });

  describe("getData", () => {
    it("calls getUserEntity with correct params", async () => {
      const wrapper = shallow<UserTopEntity>(<UserTopEntity {...props} />);
      const instance = wrapper.instance();

      const spy = jest.spyOn(instance.APIService, "getUserEntity");
      spy.mockImplementation((): any => Promise.resolve(userArtists));
      await instance.getData();

      expect(spy).toHaveBeenCalledWith(
        props?.user?.name,
        "artist",
        "week",
        0,
        10
      );
      wrapper.unmount();
    });

    it("sets state correctly if data is not calculated", async () => {
      const wrapper = shallow<UserTopEntity>(<UserTopEntity {...props} />);
      const instance = wrapper.instance();

      const spy = jest.spyOn(instance.APIService, "getUserEntity");
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
      wrapper.unmount();
    });

    it("throws error", async () => {
      const wrapper = shallow<UserTopEntity>(<UserTopEntity {...props} />);
      const instance = wrapper.instance();

      const spy = jest.spyOn(instance.APIService, "getUserEntity");
      const notFoundError = new APIError("NOT FOUND");
      notFoundError.response = {
        status: 404,
      } as Response;
      spy.mockImplementation(() => Promise.reject(notFoundError));

      await expect(instance.getData()).rejects.toThrow("NOT FOUND");
      wrapper.unmount();
    });
  });
});
