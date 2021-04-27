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
import FollowerFollowingModal from "../follow/FollowerFollowingModal";
import BrainzPlayer from "../BrainzPlayer";
import * as timelineProps from "./__mocks__/timelineProps.json";

// typescript doesn't recognise string literal values
const props = {
  ...timelineProps,
  events: timelineProps.events as TimelineEvent[],
  spotify: timelineProps.spotify as SpotifyUser,
};

describe("<UserFeed />", () => {
  beforeAll(() => {
    timeago.ago = jest.fn().mockImplementation(() => "1 day ago");
  });
  it("renders correctly", () => {
    const wrapper = shallow(<UserFeedPage {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
  });

  it("contains the FollowerFollowingModal", () => {
    const wrapper = shallow(<UserFeedPage {...props} />);
    expect(wrapper).toBeTruthy();
    expect(wrapper.find(FollowerFollowingModal)).toHaveLength(1);
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

  it("renders playlist created events", () => {
    const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />);
    const playlistEvent = wrapper.find("#timeline > ul >li").at(5);
    const description = playlistEvent.find(".event-description-text");
    expect(description.text()).toEqual(
      // @ts-ignore
      `We created a playlist for you: ${props.events[5].metadata.title}`
    );
    const content = playlistEvent.find(".event-content");
    expect(content.exists()).toBeFalsy();
    const time = playlistEvent.find(".event-time");
    expect(time.text()).toEqual("Feb 16, 11:17 AM");
  });

  describe("Pagination", () => {
    const pushStateSpy = jest.spyOn(window.history, "pushState");

    afterEach(() => {
      jest.clearAllMocks();
    });

    describe("handleClickOlder", () => {
      it("does nothing if there is no older events timestamp", async () => {
        const wrapper = shallow<UserFeedPage>(<UserFeedPage {...props} />);
        const instance = wrapper.instance();

        wrapper.setState({ nextEventTs: undefined });

        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
        // eslint-disable-next-line dot-notation
        instance["APIService"].getFeedForUser = spy;

        await instance.handleClickOlder();
        expect(wrapper.state("loading")).toBeFalsy();
        expect(spy).not.toHaveBeenCalled();
      });

      it("calls the API to get older events", async () => {
        const wrapper = shallow<UserFeedPage>(<UserFeedPage {...props} />);
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
        // eslint-disable-next-line dot-notation
        instance["APIService"].getFeedForUser = spy;

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
        const wrapper = shallow<UserFeedPage>(<UserFeedPage {...props} />);
        const instance = wrapper.instance();

        wrapper.setState({ nextEventTs: 1586450000 });

        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
        // eslint-disable-next-line dot-notation
        instance["APIService"].getFeedForUser = spy;

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
        const wrapper = shallow<UserFeedPage>(<UserFeedPage {...props} />);
        const instance = wrapper.instance();

        // Random nextEventTs to ensure that is the value set in browser history
        wrapper.setState({ events: [], nextEventTs: 1586440600 });

        const sortedEvents = sortBy(props.events, "created").reverse();
        const nextEventTs = sortedEvents[sortedEvents.length - 1].created;
        const previousEventTs = sortedEvents[0].created;

        const spy = jest.fn().mockImplementation((username, minTs, maxTs) => {
          return Promise.resolve(sortedEvents);
        });
        // eslint-disable-next-line dot-notation
        instance["APIService"].getFeedForUser = spy;

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
        const wrapper = shallow<UserFeedPage>(<UserFeedPage {...props} />);
        const instance = wrapper.instance();

        wrapper.setState({ previousEventTs: undefined });

        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
        // eslint-disable-next-line dot-notation
        instance["APIService"].getFeedForUser = spy;

        await instance.handleClickNewer();
        expect(wrapper.state("loading")).toBeFalsy();
        expect(spy).not.toHaveBeenCalled();
      });

      it("calls the API to get older events", async () => {
        const wrapper = shallow<UserFeedPage>(<UserFeedPage {...props} />);
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
        // eslint-disable-next-line dot-notation
        instance["APIService"].getFeedForUser = spy;

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

      it("sets nextEventTs to undefined if it receives no events from API", async () => {
        const wrapper = shallow<UserFeedPage>(<UserFeedPage {...props} />);
        const instance = wrapper.instance();

        wrapper.setState({ previousEventTs: 123456 });

        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
        // eslint-disable-next-line dot-notation
        instance["APIService"].getFeedForUser = spy;

        await instance.handleClickNewer();
        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("previousEventTs")).toBeUndefined();
        expect(pushStateSpy).not.toHaveBeenCalled();
      });

      it("sets the events, nextEventTs and  previousEventTs on the state and updates browser history", async () => {
        const wrapper = shallow<UserFeedPage>(<UserFeedPage {...props} />);
        const instance = wrapper.instance();

        wrapper.setState({ previousEventTs: 123456 });

        const sortedEvents = sortBy(props.events, "created");
        const nextEventTs = sortedEvents[props.events.length - 1].created;
        const previousEventTs = sortedEvents[0].created;

        const spy = jest.fn().mockImplementation((username, minTs, maxTs) => {
          return Promise.resolve(sortedEvents);
        });
        // eslint-disable-next-line dot-notation
        instance["APIService"].getFeedForUser = spy;

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
