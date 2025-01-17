import * as React from "react";
import fetchMock from "jest-fetch-mock";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import UserFeedback, {
  UserFeedbackProps,
} from "../../../src/user/taste/components/UserFeedback";
import * as userFeedbackProps from "../../__mocks__/userFeedbackProps.json";
import * as userFeedbackAPIResponse from "../../__mocks__/userFeedbackAPIResponse.json";
import { ReactQueryWrapper } from "../../test-react-query";

const { totalCount, user, feedback } = userFeedbackProps;

const userEventSession = userEvent.setup();
jest.unmock("react-toastify");

// Typescript does not like the "score“ field
const typedFeedback = feedback as FeedbackResponseWithTrackMetadata[];

const props: UserFeedbackProps = {
  totalCount,
  user,
  feedback: typedFeedback,
};

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

describe("UserFeedback", () => {
  beforeAll(() => {
    fetchMock.enableMocks();
  });

  it("renders ListenCard items for each feedback item", async () => {
    render(
      <ReactQueryWrapper>
        <UserFeedback {...props} />
      </ReactQueryWrapper>
    );
    const listensContainer = screen.getByTestId("userfeedback-listens");
    expect(listensContainer).toBeInTheDocument();
    expect(screen.getAllByTestId("listen")).toHaveLength(15);
  });

  it("does not render ListenCard items for feedback item without track name", async () => {
    const withoutTrackNameProps = {
      ...props,
      feedback: [
        {
          created: 1631778335,
          recording_msid: "8aa379ad-852e-4794-9c01-64959f5d0b17",
          score: 1,
          track_metadata: {
            additional_info: {
              recording_mbid: "9812475d-c800-4f29-8a9a-4ac4af4b4dfd",
              release_mbid: "17276c50-dd38-4c62-990e-186ef0ff36f4",
            },
            artist_name: "Hobocombo",
            release_name: "",
            track_name: "Bird's lament",
          },
          user_id: "mr_monkey",
        },
        {
          created: 1631553259,
          recording_msid: "edfa0bb9-a58c-406c-9f7c-f16741443f9c",
          score: 1,
          track_metadata: null,
          user_id: "mr_monkey",
        },
      ],
    };
    render(
      <ReactQueryWrapper>
        <UserFeedback {...(withoutTrackNameProps as UserFeedbackProps)} />
      </ReactQueryWrapper>
    );
    const listensContainer = screen.getByTestId("userfeedback-listens");
    expect(listensContainer).toBeInTheDocument();
    expect(screen.getAllByTestId("listen")).toHaveLength(1);
  });

  describe("getFeedbackItemsFromAPI", () => {
    it("sets the state and updates browser history", async () => {
      render(
        <ReactQueryWrapper>
          <UserFeedback {...props} />
        </ReactQueryWrapper>
      );

      fetchMock.mockResponseOnce(JSON.stringify(userFeedbackAPIResponse));

      // Initially set to 1 page (15 listens), after API response should be 2 pages
      const loadMoreButton = await screen.findByTitle("Load more…");
      expect(loadMoreButton).toHaveTextContent("No more feedback to show");
      expect(loadMoreButton).toBeDisabled();

      expect(screen.getAllByTestId("listen")).toHaveLength(15);
      // Click the "loved" pill button even though we are already on "loved"
      // to trigger an API call
      const lovedButton = await screen.findByRole("button", { name: /Loved/m });
      await userEventSession.click(lovedButton);

      expect(loadMoreButton).not.toBeDisabled();
      expect(screen.getAllByTestId("listen")).toHaveLength(25);
    });
  });
});
