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
});
