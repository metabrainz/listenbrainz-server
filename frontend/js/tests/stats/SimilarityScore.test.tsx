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
  let wrapper: ReactWrapper<any, any, any> | undefined;
  beforeEach(() => {
    wrapper = undefined;
  });
  afterEach(() => {
    if (wrapper) {
      /* Unmount the wrapper at the end of each test, otherwise react-dom throws errors
        related to async lifecycle methods run against a missing dom 'document'.
        See https://github.com/facebook/react/issues/15691
      */
      wrapper.unmount();
    }
  });
  it("renders correctly for type = 'regular'", () => {
    wrapper = mount<SimilarityScoreProps>(<SimilarityScore {...props} />);
    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly for type = 'compact'", () => {
    wrapper = mount<SimilarityScoreProps>(
      <SimilarityScore {...{ ...props, type: "compact" }} />
    );

    expect(wrapper).toMatchSnapshot();
  });

  it("updates the class name based on similiarty score", async () => {
    /* sets class red for score 0.2 */
    wrapper = mount<SimilarityScoreProps>(<SimilarityScore {...props} />);
    expect(wrapper.find(".progress").childAt(0).hasClass("red")).toEqual(true);

    /* sets class orange for score 0.5 */
    wrapper = mount<SimilarityScoreProps>(
      <SimilarityScore {...{ ...props, similarityScore: 0.57457 }} />
    );
    await waitForComponentToPaint(wrapper);
    expect(wrapper.find(".progress").childAt(0).hasClass("orange")).toEqual(
      true
    );

    /* sets class purple for score 0.9 */
    wrapper = mount<SimilarityScoreProps>(
      <SimilarityScore {...{ ...props, similarityScore: 0.945792 }} />
    );
    await waitForComponentToPaint(wrapper);
    expect(wrapper.find(".progress").childAt(0).hasClass("purple")).toEqual(
      true
    );
  });
});
