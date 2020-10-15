import * as React from "react";
import { mount, shallow } from "enzyme";

import RecommendationCard, {
  RecommendationCardProps,
} from "./RecommendationCard";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const recommendation: Recommendation = {
  listened_at: 0,
  track_metadata: {
    artist_name: "Kishore Kumar",
    track_name: "Ek chatur naar",
    additional_info: {
      release_mbid: "yyyy",
      artist_mbids: ["xxxx"],
    },
  },
};

const props: RecommendationCardProps = {
  recommendation,
  isCurrentUser: true,
  currentUser: { auth_token: "lalala", name: "test" },
  playRecommendation: () => {},
};

describe("RecommendationCard", () => {
  it("renders correctly for recommendations", () => {
    const wrapper = mount<RecommendationCard>(
      <RecommendationCard {...props} />
    );

    expect(wrapper).toMatchSnapshot();
  });
});
