import * as React from "react";
import { mount, shallow } from "enzyme";

import APIError from "../../src/utils/APIError";
import UserTopEntity, {
  UserTopEntityProps,
} from "../../src/stats/UserTopEntity";
import * as userArtists from "../__mocks__/userArtists.json";
import * as userReleases from "../__mocks__/userReleases.json";
import * as userRecordings from "../__mocks__/userRecordings.json";

const userProps: UserTopEntityProps = {
  range: "week",
  entity: "artist",
  apiUrl: "foobar",
  terminology: "artist",
  user: {
    name: "test_user",
  },
};

const sitewideProps: UserTopEntityProps = {
  range: "week",
  entity: "artist",
  apiUrl: "foobar",
  terminology : "artist",
};

describe.each([
  ["User Stats", userProps],
  ["Sitewide Stats", sitewideProps],
])("%s", (name, props) => {
  describe("UserTopEntity", () => {
    it("renders correctly for artist", () => {
      const wrapper = mount<UserTopEntity>(<UserTopEntity {...props} />);

      wrapper.setState({
        data: userArtists as UserArtistsResponse,
        loading: false,
      });
      wrapper.update();

      expect(wrapper).toMatchSnapshot();
    });

    it("renders correctly for release", () => {
      const wrapper = mount<UserTopEntity>(
        <UserTopEntity {...{ ...props, entity: "release" }} />
      );

      wrapper.setState({
        data: userReleases as UserReleasesResponse,
        loading: false,
      });
      wrapper.update();

      expect(wrapper).toMatchSnapshot();
    });

    it("renders correctly for recording", () => {
      const wrapper = mount<UserTopEntity>(
        <UserTopEntity {...{ ...props, entity: "recording" }} />
      );

      wrapper.setState({
        data: userRecordings as UserRecordingsResponse,
        loading: false,
      });
      wrapper.update();

      expect(wrapper).toMatchSnapshot();
    });

    it("renders corectly when range is invalid", () => {
      const wrapper = mount<UserTopEntity>(<UserTopEntity {...props} />);

      wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
      wrapper.setState({ loading: false });
      wrapper.update();

      expect(wrapper).toMatchSnapshot();
    });
  });

  describe("componentDidUpdate", () => {
    it("it sets correct state if range is incorrect", () => {
      const wrapper = shallow<UserTopEntity>(<UserTopEntity {...props} />);

      wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
      wrapper.update();

      expect(wrapper.state()).toMatchObject({
        loading: false,
        hasError: true,
        errorMessage: "Invalid range: invalid_range",
      });
    });

    it("calls loadData once if range is valid", () => {
      const wrapper = shallow<UserTopEntity>(<UserTopEntity {...props} />);
      const instance = wrapper.instance();

      instance.loadData = jest.fn();
      wrapper.setProps({ range: "month" });
      wrapper.update();

      expect(instance.loadData).toHaveBeenCalledTimes(1);
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
    });
  });
});
