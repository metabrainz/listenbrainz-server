import * as React from "react";
import { mount } from "enzyme";
import UserFeedback, {
  UserFeedbackProps,
  UserFeedbackState,
} from "./UserFeedback";
import GlobalAppContext, { GlobalAppContextT } from "./GlobalAppContext";
import APIService from "./APIService";
import * as userFeedbackProps from "./__mocks__/userFeedbackProps.json";
import ListenCard from "./listens/ListenCard";

const { totalCount, user, feedback, youtube, spotify } = userFeedbackProps;

// Typescript does not like the "score“ field
const typedFeedback = feedback as FeedbackResponseWithTrackMetadata[];

const props = {
  totalCount,
  user,
  feedback: typedFeedback,
  youtube,
  spotify,
  newAlert: () => {},
};

// Create a new instance of GlobalAppContext
const mountOptions: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIService("foo"),
    youtubeAuth: youtube as YoutubeUser,
    spotifyAuth: spotify as SpotifyUser,
    currentUser: { auth_token: "lalala", name: "pikachu" },
  },
};
const mountOptionsWithoutUser: { context: GlobalAppContextT } = {
  context: {
    ...mountOptions.context,
    currentUser: {} as ListenBrainzUser,
  },
};

// from https://github.com/kentor/flush-promises/blob/46f58770b14fb74ce1ff27da00837c7e722b9d06/index.js
const scheduler =
  typeof setImmediate === "function" ? setImmediate : setTimeout;

function flushPromises() {
  return new Promise(function flushPromisesPromise(resolve) {
    scheduler(resolve, 0);
  });
}

const mockDate = new Date("2021-05-19");
const fakeDateNow = jest
  .spyOn(global.Date, "now")
  .mockImplementation(() => mockDate.getTime());

describe("UserFeedback", () => {
  it("renders correctly", () => {
    const wrapper = mount<UserFeedback>(
      <UserFeedback {...props} />,
      mountOptions
    );
    expect(wrapper.html()).toMatchSnapshot();
    fakeDateNow.mockRestore();
  });

  it("loads user feedback on componentDidMount", async () => {
    const wrapper = mount<UserFeedback>(
      <GlobalAppContext.Provider value={mountOptions.context}>
        <UserFeedback {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();
    const loadFeedbackSpy = jest.spyOn(instance, "loadFeedback");
    const getFeedbackSpy = jest.spyOn(instance, "getFeedback");
    const apiGetFeedbackSpy = jest.spyOn(
      // @ts-ignore
      instance.APIService,
      "getFeedbackForUserForRecordings"
    );
    await instance.componentDidMount();
    await flushPromises();

    expect(loadFeedbackSpy).toHaveBeenCalledTimes(1);
    expect(getFeedbackSpy).toHaveBeenCalledTimes(1);
    expect(apiGetFeedbackSpy).toHaveBeenCalledTimes(1);
    expect(apiGetFeedbackSpy).toHaveBeenCalledWith(
      "pikachu",
      feedback
        .map((item) => item.recording_msid)
        .filter((item) => {
          return item !== undefined;
        })
        .join(",")
    );
  });

  it("does not load user feedback if no user is logged in", async () => {
    const wrapper = mount<UserFeedback>(
      <GlobalAppContext.Provider value={mountOptionsWithoutUser.context}>
        <UserFeedback {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();
    const loadFeedbackSpy = jest.spyOn(instance, "loadFeedback");
    const getFeedbackSpy = jest.spyOn(instance, "getFeedback");
    const apiGetFeedbackSpy = jest.spyOn(
      instance.context.APIService,
      "getFeedbackForUserForRecordings"
    );
    instance.componentDidMount();
    expect(loadFeedbackSpy).toHaveBeenCalledTimes(1);
    expect(getFeedbackSpy).toHaveBeenCalledTimes(1);

    await flushPromises();
    expect(instance.context.currentUser).toEqual({});
    expect(apiGetFeedbackSpy).not.toHaveBeenCalled();
  });

  it("renders ListenCard items for each feedback item", async () => {
    const wrapper = mount<UserFeedback>(
      <GlobalAppContext.Provider value={mountOptions.context}>
        <UserFeedback {...props} />
      </GlobalAppContext.Provider>
    );
    const listens = wrapper.find(ListenCard);
    expect(listens).toHaveLength(15);
  });

  it("shows feedback on the ListenCards according to recordingFeedbackMap", async () => {
    const wrapper = mount<UserFeedback>(
      <GlobalAppContext.Provider value={mountOptions.context}>
        <UserFeedback {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();
    instance.setState({
      recordingFeedbackMap: {
        "8aa379ad-852e-4794-9c01-64959f5d0b17": 1,
        "edfa0bb9-a58c-406c-9f7c-f16741443f9c": 0,
        "20059ffb-1615-4712-8235-a12840fb156e": -1,
      },
    });
    wrapper.update();
    const listens = wrapper.find(ListenCard);
    // Score = 1 (loved) for first item
    const firstListenCard = listens.at(1).find(".listen-controls").first();
    expect(
      firstListenCard.find("[title='Love']").first().hasClass("loved")
    ).toBeTruthy();
    // Score = 0 (neutral) for second item
    const secondListenCard = listens.at(1).find(".listen-controls").first();
    expect(
      secondListenCard.find("[title='Love']").first().hasClass("loved")
    ).toBeFalsy();
    expect(
      secondListenCard.find("[title='Hate']").first().hasClass("hated")
    ).toBeFalsy();
    // Score = -1 (hated) for third item
    const thirdListenCard = listens.at(2).find(".listen-controls").first();
    expect(
      thirdListenCard.find("[title='Hate']").first().hasClass("hated")
    ).toBeTruthy();
    // No score (neutral) for fourth item
    const fourthListenCard = listens.at(3).find(".listen-controls").first();
    expect(
      fourthListenCard.find("[title='Love']").first().hasClass("loved")
    ).toBeFalsy();
    expect(
      fourthListenCard.find("[title='Hate']").first().hasClass("hated")
    ).toBeFalsy();
  });
});
