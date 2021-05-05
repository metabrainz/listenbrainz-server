/*
 * listenbrainz-server - Server for the ListenBrainz project.
 *
 * Copyright (C) 2020 Param Singh <iliekcomputers@gmail.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

import * as React from "react";
import { mount, shallow } from "enzyme";
import * as timeago from "time-ago";
import { sortBy } from "lodash";
import UserFeedPage from "./UserFeed";
import UserSocialNetwork from "../follow/UserSocialNetwork";
import BrainzPlayer from "../BrainzPlayer";
import * as timelineProps from "./__mocks__/timelineProps.json";
import GlobalAppContext from "../GlobalAppContext";
import APIService from "../APIService";

// typescript doesn't recognise string literal values
const props = {
  ...timelineProps,
  events: timelineProps.events as TimelineEvent[],
  spotify: timelineProps.spotify as SpotifyUser,
  newAlert: () => {},
};

describe("<UserFeed />", () => {
  beforeAll(() => {
    timeago.ago = jest.fn().mockImplementation(() => "1 day ago");
  });
  it("renders correctly", () => {
    const wrapper = shallow(<UserFeedPage {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
  });

  it("contains a UserSocialNetwork component", () => {
    const wrapper = shallow(<UserFeedPage {...props} />);
    expect(wrapper).toBeTruthy();
    expect(wrapper.find(UserSocialNetwork)).toHaveLength(1);
  });

  it("contains a BrainzPlayer instance", () => {
    const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />);
    const instance = wrapper.instance();
    expect(wrapper.find(BrainzPlayer)).toHaveLength(1);
    // eslint-disable-next-line dot-notation
    expect(instance["brainzPlayer"].current).toBeInstanceOf(BrainzPlayer);
  });

  it("renders the correct number of timeline events", () => {
    const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />);
    const ulElement = wrapper.find("#timeline > ul");
    expect(ulElement).toHaveLength(1);
    expect(ulElement.children()).toHaveLength(props.events.length);
    expect(ulElement.childAt(0).is(".timeline-event")).toBeTruthy();
  });

  it("renders recording recommendation events", () => {
    const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />);
    const recEvent = wrapper.find("#timeline > ul >li").at(0);
    const description = recEvent.find(".event-description-text");
    expect(description.text()).toEqual("reosarevok recommended a track");
    const content = recEvent.find(".event-content");
    expect(content.exists()).toBeTruthy();
    expect(content.children()).toHaveLength(1);
    const time = recEvent.find(".event-time");
    expect(time.text()).toEqual("Mar 02, 7:48 PM");
  });

  it("renders follow relationship events", () => {
    const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />);
    const followedEvent = wrapper.find("#timeline > ul >li").at(3);
    let description = followedEvent.find(".event-description-text");
    expect(description.text()).toEqual("You are now following reosarevok");
    let content = followedEvent.find(".event-content");
    expect(content.exists()).toBeFalsy();
    let time = followedEvent.find(".event-time");
    expect(time.text()).toEqual("Feb 16, 11:21 AM");

    const followEvent = wrapper.find("#timeline > ul >li").at(4);
    description = followEvent.find(".event-description-text");
    expect(description.text()).toEqual("reosarevok is now following you");
    content = followEvent.find(".event-content");
    expect(content.exists()).toBeFalsy();
    time = followEvent.find(".event-time");
    expect(time.text()).toEqual("Feb 16, 11:20 AM");
  });

  it("renders notification events", () => {
    const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />);
    const notificationEvent = wrapper.find("#timeline > ul >li").at(5);
    const description = notificationEvent.find(".event-description-text");
    // Ensure it parsed and reconstituted the html message
    expect(description.text()).toEqual(
      // @ts-ignore
      `We have created a playlist for you: My top discoveries of 2020`
    );
    expect(description.html()).toEqual(
      // @ts-ignore
      '<span class="event-description-text">We have created a playlist for you: <a href="https://listenbrainz.org/playlist/4245ccd3-4f0d-4276-95d6-2e09d87b5546">My top discoveries of 2020</a></span>'
    );
    const content = notificationEvent.find(".event-content");
    expect(content.exists()).toBeFalsy();
    const time = notificationEvent.find(".event-time");
    expect(time.text()).toEqual("Feb 16, 11:17 AM");
  });

  describe("Pagination", () => {
    const pushStateSpy = jest.spyOn(window.history, "pushState");

    afterEach(() => {
      jest.clearAllMocks();
    });

    describe("handleClickOlder", () => {
      it("does nothing if there is no older events timestamp", async () => {
        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
        const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />, {
          context: {
            APIService: { getFeedForUser: spy },
          },
        });
        const instance = wrapper.instance();

        wrapper.setState({ nextEventTs: undefined });

        await instance.handleClickOlder();
        // Flush promises
        await new Promise((resolve) => setImmediate(resolve));

        expect(wrapper.state("loading")).toBeFalsy();
        expect(spy).not.toHaveBeenCalled();
      });

      it("calls the API to get older events", async () => {
        const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />);
        const instance = wrapper.instance();

        wrapper.setState({ nextEventTs: 1586450000 });
        const expectedEventsArray = [
          {
            event_type: "follow",
            created: 1613474472,
            metadata: {
              user_0: "iliekcomputers",
              user_1: "reosarevok",
              type: "follow",
            },
            user_id: "iliekcomputers",
          },
        ];
        const spy = jest
          .fn()
          .mockImplementation(() => Promise.resolve(expectedEventsArray));

        instance.context.APIService.getFeedForUser = spy;

        await instance.handleClickOlder();
        expect(spy).toHaveBeenCalledWith(
          props.currentUser.name,
          props.currentUser.auth_token,
          undefined,
          1586450000
        );
        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("events")).toEqual(expectedEventsArray);
      });

      it("sets nextEventTs to undefined if it receives no events from API", async () => {
        const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />);
        const instance = wrapper.instance();

        wrapper.setState({ nextEventTs: 1586450000 });

        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
        instance.context.APIService.getFeedForUser = spy;

        await instance.handleClickOlder();
        expect(spy).toHaveBeenCalledWith(
          props.currentUser.name,
          props.currentUser.auth_token,
          undefined,
          1586450000
        );
        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("nextEventTs")).toBeUndefined();
        expect(pushStateSpy).not.toHaveBeenCalled();
      });

      it("sets the events, nextEventTs and  previousEventTs on the state and updates browser history", async () => {
        const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />);
        const instance = wrapper.instance();

        // Random nextEventTs to ensure that is the value set in browser history
        wrapper.setState({ events: [], nextEventTs: 1586440600 });

        const sortedEvents = sortBy(props.events, "created").reverse();
        const nextEventTs = sortedEvents[sortedEvents.length - 1].created;
        const previousEventTs = sortedEvents[0].created;

        const spy = jest.fn().mockImplementation((username, minTs, maxTs) => {
          return Promise.resolve(sortedEvents);
        });
        instance.context.APIService.getFeedForUser = spy;

        await instance.handleClickOlder();

        expect(wrapper.state("events")).toEqual(sortedEvents);
        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("nextEventTs")).toEqual(nextEventTs);
        expect(wrapper.state("previousEventTs")).toEqual(previousEventTs);
        expect(pushStateSpy).toHaveBeenCalledWith(
          null,
          "",
          `?max_ts=1586440600`
        );
      });
    });

    describe("handleClickNewer", () => {
      it("does nothing if there is no newer events timestamp", async () => {
        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
        const wrapper = shallow<UserFeedPage>(<UserFeedPage {...props} />, {
          context: {
            APIService: { getFeedForUser: spy },
          },
        });
        const instance = wrapper.instance();

        wrapper.setState({ previousEventTs: undefined });

        await instance.handleClickNewer();
        expect(wrapper.state("loading")).toBeFalsy();
        expect(spy).not.toHaveBeenCalled();
      });

      it("calls the API to get newer events", async () => {
        const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />);
        const instance = wrapper.instance();
        wrapper.setState({ previousEventTs: 123456 });

        const expectedEventsArray = [
          {
            event_type: "follow",
            created: 1613474472,
            metadata: {
              user_0: "iliekcomputers",
              user_1: "reosarevok",
              type: "follow",
            },
            user_id: "iliekcomputers",
          },
        ];
        const spy = jest
          .fn()
          .mockImplementation(() => Promise.resolve(expectedEventsArray));
        instance.context.APIService.getFeedForUser = spy;

        await instance.handleClickNewer();

        expect(wrapper.state("events")).toEqual(expectedEventsArray);
        expect(wrapper.state("loading")).toBeFalsy();
        expect(spy).toHaveBeenCalledWith(
          props.currentUser.name,
          props.currentUser.auth_token,
          123456,
          undefined
        );
      });

      it("sets previousEventTs to undefined if it receives no events from API", async () => {
        const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />);
        const instance = wrapper.instance();

        wrapper.setState({ previousEventTs: 123456 });

        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));

        instance.context.APIService.getFeedForUser = spy;

        await instance.handleClickNewer();
        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("previousEventTs")).toBeUndefined();
        expect(pushStateSpy).not.toHaveBeenCalled();
      });

      it("sets the events, nextEventTs and  previousEventTs on the state and updates browser history", async () => {
        const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />);
        const instance = wrapper.instance();
        wrapper.setState({ previousEventTs: 123456 });

        const sortedEvents = sortBy(props.events, "created");
        instance.context.APIService.getFeedForUser = jest.fn(
          (username, minTs, maxTs) => {
            return Promise.resolve(sortedEvents);
          }
        );

        const nextEventTs = sortedEvents[props.events.length - 1].created;
        const previousEventTs = sortedEvents[0].created;

        await instance.handleClickNewer();

        expect(wrapper.state("events")).toEqual(sortedEvents);
        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("nextEventTs")).toEqual(nextEventTs);
        expect(wrapper.state("previousEventTs")).toEqual(previousEventTs);
        expect(pushStateSpy).toHaveBeenCalledWith(null, "", `?min_ts=123456`);
      });
    });
  });
});
