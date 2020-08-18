import * as React from "react";
import { mount, shallow } from "enzyme";

import ListenCard, {
  ListenCardProps,
  DEFAULT_COVER_ART_URL,
} from "./ListenCard";

const listen: Listen = {
  listened_at: 0,
  track_metadata: {
    artist_name: "Moondog",
    track_name: "Bird's Lament",
    additional_info: {
      release_mbid: "foo",
      recording_msid: "bar",
    },
  },
};

const props: ListenCardProps = {
  apiUrl: "foobar",
  listen,
  mode: "listens",
  playListen: () => {},
};

describe("ListenCard", () => {
  it("renders correctly for mode = 'listens'", () => {
    const wrapper = mount<ListenCard>(<ListenCard {...props} />);

    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly for mode = 'follow '", () => {
    const wrapper = mount<ListenCard>(
      <ListenCard {...{ ...props, mode: "follow" }} />
    );

    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly for mode = 'recent '", () => {
    const wrapper = mount<ListenCard>(
      <ListenCard {...{ ...props, mode: "recent" }} />
    );

    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly when coverArtUrl is set", () => {
    const wrapper = mount<ListenCard>(<ListenCard {...props} />);

    wrapper.setState({
      coverArtUrl:
        "https://i.scdn.co/image/ab67616d00004851d976f08a9feba38efcafb5ff",
    });
    wrapper.update();

    expect(wrapper).toMatchSnapshot();
  });
});

describe("componentDidMount", () => {
  it("calls getCoverArt", () => {
    const wrapper = shallow<ListenCard>(<ListenCard {...props} />);
    const instance = wrapper.instance();
    instance.getCoverArt = jest.fn();

    instance.componentDidMount();

    expect(instance.getCoverArt).toHaveBeenCalledTimes(1);
  });
});

describe("getCoverArt", () => {
  it("updates coverArtUrl state", async () => {
    const wrapper = shallow<ListenCard>(<ListenCard {...props} />);
    const instance = wrapper.instance();
    const imageUrl =
      "https://i.scdn.co/image/ab67616d00004851d976f08a9feba38efcafb5ff";

    const spy = jest.spyOn(instance.APIService, "getCoverArt");
    spy.mockImplementation(() => Promise.resolve(imageUrl));

    expect(wrapper.state("coverArtUrl")).toBeUndefined();
    await instance.componentDidMount();

    expect(spy).toHaveBeenCalledWith("foo", "bar");
    expect(wrapper.state("coverArtUrl")).toEqual(imageUrl);
  });

  it("sets coverArtUrl state to DEFAULT_COVER_ART_URL when API returns null", async () => {
    const wrapper = shallow<ListenCard>(<ListenCard {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "getCoverArt");
    spy.mockImplementation(() => Promise.resolve(null));

    expect(wrapper.state("coverArtUrl")).toBeUndefined();
    await instance.componentDidMount();

    expect(spy).toHaveBeenCalledWith("foo", "bar");
    expect(wrapper.state("coverArtUrl")).toEqual(DEFAULT_COVER_ART_URL);
  });
});
