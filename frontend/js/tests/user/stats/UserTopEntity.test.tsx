import * as React from "react";
import { mount, ReactWrapper, shallow, ShallowWrapper } from "enzyme";

import { act } from "react-dom/test-utils";
import { BrowserRouter } from "react-router-dom";
import APIError from "../../../src/utils/APIError";
import UserTopEntity, {
  UserTopEntityProps,
} from "../../../src/user/stats/components/UserTopEntity";
import * as userArtists from "../../__mocks__/userArtists.json";
import * as userReleases from "../../__mocks__/userReleases.json";
import * as userRecordings from "../../__mocks__/userRecordings.json";
import * as userReleaseGroups from "../../__mocks__/userReleaseGroups.json";
import { waitForComponentToPaint } from "../../test-utils";
import ListenCard from "../../../src/common/listens/ListenCard";

const userProps: UserTopEntityProps = {
  range: "week",
  entity: "artist",
  terminology: "artist",
  user: {
    name: "test_user",
  },
};

const sitewideProps: UserTopEntityProps = {
  range: "week",
  entity: "artist",
  terminology: "artist",
};

describe.each([
  ["User Stats", userProps],
  ["Sitewide Stats", sitewideProps],
])("%s", (name, props) => {
  const getComponent = (componentProps: UserTopEntityProps) => (
    <BrowserRouter>
      <UserTopEntity {...componentProps} />
    </BrowserRouter>
  );

  describe("UserTopEntity", () => {
    it("renders correctly for artist", async () => {});
  });

  //   describe("UserTopEntity", () => {
  //     it("renders correctly for artist", async () => {
  //       const wrapper = mount(getComponent(props));
  //       await act(() => {
  //         wrapper
  //           .find(UserTopEntity)
  //           .instance()
  //           .setState({
  //             data: userArtists as UserArtistsResponse,
  //             loading: false,
  //           });
  //       });
  //       await waitForComponentToPaint(wrapper);

  //       expect(wrapper.find(ListenCard)).toHaveLength(25);
  //       expect(wrapper.find("h3").getDOMNode()).toHaveTextContent("Top artists");
  //       wrapper.unmount();
  //     });

  //     it("renders correctly for release", async () => {
  //       const wrapper = mount(
  //         <BrowserRouter>
  //           <UserTopEntity {...props} entity="release" terminology="release" />
  //         </BrowserRouter>
  //       );
  //       const instance = wrapper.find(UserTopEntity).instance();
  //       instance.setState({
  //         data: userReleases as UserReleasesResponse,
  //         loading: false,
  //       });
  //       wrapper.update();
  //       await waitForComponentToPaint(wrapper);
  //       expect(wrapper.find(UserTopEntity).state("data")).toEqual(userReleases);

  //       expect(wrapper.find(ListenCard)).toHaveLength(25);
  //       expect(wrapper.find("h3").getDOMNode()).toHaveTextContent("Top releases");
  //       wrapper.unmount();
  //     });

  //     it("renders correctly for release group", async () => {
  //       const wrapper = mount(
  //         <BrowserRouter>
  //           <UserTopEntity
  //             {...props}
  //             entity="release-group"
  //             terminology="album"
  //           />
  //         </BrowserRouter>
  //       );
  //       const instance = wrapper.find(UserTopEntity).instance();
  //       await act(() => {
  //         instance.setState({
  //           data: userReleaseGroups as UserReleaseGroupsResponse,
  //           loading: false,
  //         });
  //       });
  //       await waitForComponentToPaint(wrapper);

  //       expect(wrapper.find("h3").getDOMNode()).toHaveTextContent("Top albums");
  //       expect(wrapper.find(ListenCard)).toHaveLength(25);
  //       wrapper.unmount();
  //     });

  //     it("renders correctly for recording", async () => {
  //       const wrapper = mount(
  //         <BrowserRouter>
  //           <UserTopEntity {...props} entity="recording" terminology="track" />
  //         </BrowserRouter>
  //       );
  //       const instance = wrapper.find(UserTopEntity).instance();
  //       await act(() => {
  //         instance.setState({
  //           data: userRecordings as UserRecordingsResponse,
  //           loading: false,
  //         });
  //       });
  //       await waitForComponentToPaint(wrapper);

  //       expect(wrapper.find("h3").getDOMNode()).toHaveTextContent("Top tracks");
  //       expect(wrapper.find(ListenCard)).toHaveLength(25);
  //       wrapper.unmount();
  //     });

  //     it("renders corectly when range is invalid", async () => {
  //       const wrapper = mount(
  //         React.createElement((componentProps: UserTopEntityProps) => (
  //           <BrowserRouter>
  //             <UserTopEntity
  //               {...componentProps}
  //               entity="recording"
  //               terminology="track"
  //             />
  //           </BrowserRouter>
  //         ))
  //       );
  //       const instance = wrapper.find(UserTopEntity).instance();
  //       await act(() => {
  //         wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
  //         instance.setState({ loading: false });
  //       });
  //       await waitForComponentToPaint(wrapper);

  //       expect(wrapper.find(UserTopEntity).getDOMNode()).toHaveTextContent(
  //         "Invalid range: invalid_range"
  //       );
  //       wrapper.unmount();
  //     });
  //   });

  //   describe("componentDidUpdate", () => {
  //     // eslint-disable-next-line jest/no-disabled-tests
  //     xit("it sets correct state if range is incorrect", async () => {
  //       const wrapper = shallow(
  //         React.createElement((componentProps: UserTopEntityProps) => (
  //           <BrowserRouter>
  //             <UserTopEntity {...componentProps} />
  //           </BrowserRouter>
  //         ))
  //       );
  //       await act(() => {
  //         wrapper.setProps({ range: "invalid_range" as UserStatsAPIRange });
  //       });
  //       await waitForComponentToPaint(wrapper);
  //       const childElement = shallow(wrapper.find(UserTopEntity).get(0));

  //       expect(childElement.find(UserTopEntity).state()).toMatchObject({
  //         loading: false,
  //         hasError: true,
  //         errorMessage: "Invalid range: invalid_range",
  //       });
  //       wrapper.unmount();
  //     });

  //     it("calls loadData once if range is valid", async () => {
  //       const wrapper = mount(
  //         React.createElement((componentProps: UserTopEntityProps) => (
  //           <BrowserRouter>
  //             <UserTopEntity {...componentProps} />
  //           </BrowserRouter>
  //         ))
  //       );

  //       const instance = wrapper.find(UserTopEntity).instance() as UserTopEntity;

  //       instance.loadData = jest.fn();
  //       await act(() => {
  //         wrapper.setProps({ range: "month" });
  //       });
  //       await waitForComponentToPaint(wrapper);

  //       expect(instance.loadData).toHaveBeenCalledTimes(1);
  //       wrapper.unmount();
  //     });
  //   });

  //   describe("loadData", () => {
  //     it("calls getData once", async () => {
  //       const wrapper = shallow(getComponent(props));
  //       const childElement = shallow(wrapper.find(UserTopEntity).get(0));
  //       const instance = childElement.instance() as UserTopEntity;

  //       instance.getData = jest
  //         .fn()
  //         .mockImplementationOnce(() => Promise.resolve(userArtists));
  //       await instance.loadData();

  //       expect(instance.getData).toHaveBeenCalledTimes(1);
  //       wrapper.unmount();
  //     });

  //     it("set state correctly", async () => {
  //       const wrapper = shallow(getComponent(props));
  //       const childElement = shallow(wrapper.find(UserTopEntity).get(0));
  //       const instance = childElement.instance() as UserTopEntity;

  //       instance.getData = jest
  //         .fn()
  //         .mockImplementationOnce(() => Promise.resolve(userArtists));
  //       await instance.loadData();

  //       expect(childElement.state()).toMatchObject({
  //         data: userArtists,
  //         loading: false,
  //       });
  //       wrapper.unmount();
  //     });
  //   });

  //   describe("getData", () => {
  //     it("calls getUserEntity with correct params", async () => {
  //       const wrapper = shallow(getComponent(props));
  //       const childElement = shallow(wrapper.find(UserTopEntity).get(0));
  //       const instance = childElement.instance() as UserTopEntity;

  //       const spy = jest.spyOn(instance.APIService, "getUserEntity");
  //       spy.mockImplementation((): any => Promise.resolve(userArtists));
  //       await instance.getData();

  //       expect(spy).toHaveBeenCalledWith(
  //         props?.user?.name,
  //         "artist",
  //         "week",
  //         0,
  //         10
  //       );
  //       wrapper.unmount();
  //     });

  //     it("sets state correctly if data is not calculated", async () => {
  //       const wrapper = shallow(getComponent(props));
  //       const childElement = shallow(wrapper.find(UserTopEntity).get(0));
  //       const instance = childElement.instance() as UserTopEntity;

  //       const spy = jest.spyOn(instance.APIService, "getUserEntity");
  //       const noContentError = new APIError("NO CONTENT");
  //       noContentError.response = {
  //         status: 204,
  //       } as Response;
  //       spy.mockImplementation(() => Promise.reject(noContentError));
  //       await instance.getData();

  //       expect(childElement.state()).toMatchObject({
  //         loading: false,
  //         hasError: true,
  //         errorMessage: "NO CONTENT",
  //       });
  //       wrapper.unmount();
  //     });
  //   });
});
