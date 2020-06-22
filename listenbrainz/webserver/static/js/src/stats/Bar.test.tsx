import * as React from "react";
import { shallow } from "enzyme";

import Bar, { BarProps } from "./Bar";
import * as userRecordingsProcessDataOutput from "../__mocks__/userRecordingsProcessData.json";

const props: BarProps = {
  data: userRecordingsProcessDataOutput as UserEntityData,
  maxValue: userRecordingsProcessDataOutput[24].count,
};

describe("getEntityLink", () => {
  it("returns anchor element if entityMBID is present", () => {
    const wrapper = shallow<Bar>(<Bar {...props} />);
    const instance = wrapper.instance();

    const result = shallow(
      instance.getEntityLink(
        {
          id: "0",
          idx: 0,
          entity: "test",
          entityType: "recording",
          entityMBID: "1234",
          count: 0,
        },
        "test"
      )
    );

    expect(
      result.equals(
        <a
          href="http://musicbrainz.org/recording/1234"
          target="_blank"
          rel="noopener noreferrer"
        >
          test
        </a>
      )
    ).toEqual(true);
  });

  it("returns string if entityMBID is not present", () => {
    const wrapper = shallow<Bar>(<Bar {...props} />);
    const instance = wrapper.instance();

    const result = instance.getEntityLink(
      {
        id: "0",
        idx: 0,
        entity: "test",
        entityType: "recording",
        count: 0,
      },
      "test"
    );

    expect(result).toEqual(<>test</>);
  });
});

describe("getArtistLink", () => {
  it("returns anchor element if artistMBID is present", () => {
    const wrapper = shallow<Bar>(<Bar {...props} />);
    const instance = wrapper.instance();

    const result = shallow(
      instance.getArtistLink(
        {
          id: "0",
          idx: 0,
          entity: "test",
          entityType: "recording",
          artist: "foobar",
          artistMBID: ["1234"],
          count: 0,
        },
        "foobar"
      )
    );

    expect(
      result.equals(
        <a
          href="http://musicbrainz.org/artist/1234"
          target="_blank"
          rel="noopener noreferrer"
        >
          foobar
        </a>
      )
    ).toEqual(true);
  });

  it("returns string if artistMBID is not present", () => {
    const wrapper = shallow<Bar>(<Bar {...props} />);
    const instance = wrapper.instance();

    const result = instance.getArtistLink(
      {
        id: "0",
        idx: 0,
        entity: "test",
        entityType: "recording",
        artist: "foobar",
        count: 0,
      },
      "foobar"
    );

    expect(result).toEqual(<>foobar</>);
  });
});

describe("getReleaseLink", () => {
  it("returns anchor element if releaseMBID is present", () => {
    const wrapper = shallow<Bar>(<Bar {...props} />);
    const instance = wrapper.instance();

    const result = shallow(
      instance.getReleaseLink(
        {
          id: "0",
          idx: 0,
          entity: "test",
          entityType: "recording",
          release: "barfoo",
          releaseMBID: "1234",
          count: 0,
        },
        "barfoo"
      )
    );

    expect(
      result.equals(
        <a
          href="http://musicbrainz.org/release/1234"
          target="_blank"
          rel="noopener noreferrer"
        >
          barfoo
        </a>
      )
    ).toEqual(true);
  });

  it("returns string if artistMBID is not present", () => {
    const wrapper = shallow<Bar>(<Bar {...props} />);
    const instance = wrapper.instance();

    const result = instance.getReleaseLink(
      {
        id: "0",
        idx: 0,
        entity: "test",
        entityType: "recording",
        artist: "foobar",
        count: 0,
      },
      "barfoo"
    );

    expect(result).toEqual(<>barfoo</>);
  });
});
