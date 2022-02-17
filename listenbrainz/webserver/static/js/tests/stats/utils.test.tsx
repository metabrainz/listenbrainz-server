import { mount } from "enzyme";

import { getEntityLink } from "../../src/stats/utils";

describe("getEntityLink", () => {
  it("renders a link if MBID is provided", () => {
    const wrapper = mount(getEntityLink("artist", "test_artist", "test_mbid"));
    expect(wrapper).toMatchSnapshot();
  });

  it("renders a string if MBID is not provided", () => {
    const wrapper = mount(getEntityLink("artist", "test_artist"));
    expect(wrapper).toMatchSnapshot();
  });
});
