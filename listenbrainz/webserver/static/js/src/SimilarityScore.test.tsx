import * as React from "react";
import { mount } from "enzyme";

import SimilarityScore, { SimilarityScoreProps } from "./SimilarityScore";

const props: SimilarityScoreProps = {
  similarityScore: 0.2,
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

  it("updates the class name based on similiarty score", () => {
    /* sets class red for score 0.2 */
    let wrapper = mount<SimilarityScoreProps>(<SimilarityScore {...props} />);
    expect(wrapper.find(".progress").childAt(0).hasClass("red")).toEqual(true);

    /* sets class orange for score 0.5 */
    wrapper = mount<SimilarityScoreProps>(
      <SimilarityScore {...{ ...props, similarityScore: 0.5 }} />
    );
    expect(wrapper.find(".progress").childAt(0).hasClass("orange")).toEqual(
      true
    );

    /* sets class purple for score 0.9 */
    wrapper = mount<SimilarityScoreProps>(
      <SimilarityScore {...{ ...props, similarityScore: 0.9 }} />
    );
    expect(wrapper.find(".progress").childAt(0).hasClass("purple")).toEqual(
      true
    );
  });
});
