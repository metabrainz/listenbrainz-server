import * as React from "react";
import { mount, ReactWrapper } from "enzyme";

import SimilarityScore, {
  SimilarityScoreProps,
} from "../../src/stats/SimilarityScore";
import { waitForComponentToPaint } from "../test-utils";

const props: SimilarityScoreProps = {
  similarityScore: 0.239745792,
  user: { auth_token: "baz", name: "test" },
  type: "regular",
};

describe("SimilarityScore", () => {
  it("renders correctly for type = 'regular'", () => {
    const wrapper = mount<SimilarityScoreProps>(<SimilarityScore {...props} />);
    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly for type = 'compact'", () => {
    const wrapper = mount<SimilarityScoreProps>(
      <SimilarityScore {...{ ...props, type: "compact" }} />
    );

    expect(wrapper).toMatchSnapshot();
  });

  it("updates the class name based on similiarty score", async () => {
    /* sets class red for score 0.2 */
    const wrapper = mount<SimilarityScoreProps>(<SimilarityScore {...props} />);
    expect(wrapper.find(".progress").childAt(0).hasClass("red")).toEqual(true);

    /* sets class orange for score 0.5 */
    wrapper.setProps({ similarityScore: 0.57457 });
    await waitForComponentToPaint(wrapper);
    expect(wrapper.find(".progress").childAt(0).hasClass("orange")).toEqual(
      true
    );

    /* sets class purple for score 0.9 */
    wrapper.setProps({ similarityScore: 0.945792 });
    await waitForComponentToPaint(wrapper);
    expect(wrapper.find(".progress").childAt(0).hasClass("purple")).toEqual(
      true
    );
  });
});
