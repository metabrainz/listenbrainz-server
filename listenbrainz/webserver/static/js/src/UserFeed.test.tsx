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
import { before } from "lodash";
import UserFeedPage from "./UserFeed";
import FollowerFollowingModal from "./follow/FollowerFollowingModal";
import BrainzPlayer from "./BrainzPlayer";
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
    expect(description.text()).toEqual("reosarevok recommended a song");
    const content = recEvent.find(".event-content");
    expect(content.exists()).toBeTruthy();
    expect(content.children()).toHaveLength(1);
    const time = recEvent.find(".event-time");
    expect(time.text()).toEqual("Tue, Mar 2, 2021, 7 PM");
  });

  it("renders follow relationship events", () => {
    const wrapper = mount<UserFeedPage>(<UserFeedPage {...props} />);
    const followedEvent = wrapper.find("#timeline > ul >li").at(3);
    let description = followedEvent.find(".event-description-text");
    expect(description.text()).toEqual("You are now following reosarevok");
    let content = followedEvent.find(".event-content");
    expect(content.exists()).toBeFalsy();
    let time = followedEvent.find(".event-time");
    expect(time.text()).toEqual("Tue, Feb 16, 2021, 11 AM");

    const followEvent = wrapper.find("#timeline > ul >li").at(4);
    description = followEvent.find(".event-description-text");
    expect(description.text()).toEqual("reosarevok is now following you");
    content = followEvent.find(".event-content");
    expect(content.exists()).toBeFalsy();
    time = followEvent.find(".event-time");
    expect(time.text()).toEqual("Tue, Feb 16, 2021, 11 AM");
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
    expect(time.text()).toEqual("Tue, Feb 16, 2021, 11 AM");
  });
});
