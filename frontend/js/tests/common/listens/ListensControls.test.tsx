import * as React from "react";
import fetchMock from "jest-fetch-mock";

import {
  screen,
  waitForElementToBeRemoved,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";
import * as recentListensPropsOneListen from "../../__mocks__/recentListensPropsOneListen.json";
import * as recentListensPropsThreeListens from "../../__mocks__/recentListensPropsThreeListens.json";
import * as getFeedbackByMsidResponse from "../../__mocks__/getFeedbackByMsidResponse.json";
import * as getMultipleFeedbackResponse from "../../__mocks__/getMultipleFeedbackResponse.json";
import Listens, { ListensProps } from "../../../src/user/Dashboard";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

jest.unmock("react-toastify");

const {
  latestListenTs,
  listens,
  oldestListenTs,
  user,
  currentUser,
} = recentListensPropsOneListen;

const props: ListensProps = {
  latestListenTs,
  listens,
  oldestListenTs,
  user,
  already_reported_user: false,
};

// const userEventSession = userEvent.setup();

// eslint-disable-next-line jest/no-disabled-tests
xdescribe("ListensControls", () => {
  describe("removeListenFromListenList", () => {
    beforeAll(() => {
      fetchMock.enableMocks();
      fetchMock.doMock();
      fetchMock.mockIf(
        (input) => input.url.endsWith("/listen-count"),
        () => {
          return Promise.resolve(JSON.stringify({ payload: { count: 42 } }));
        }
      );

      fetchMock.mockIf(
        (input) => input.url.endsWith("/delete-listen"),
        () => Promise.resolve({ status: 200, statusText: "ok" })
      );
    });
    it("updates the listens state for particular recording", async () => {});
    // it("updates the listens state for particular recording", async () => {
    //   renderWithProviders(<Listens {...props} />, {
    //     currentUser: {
    //       id: 1,
    //       name: "iliekcomputers",
    //       auth_token: "never_gonna",
    //     },
    //   });

    //   const listenCards = screen.getAllByTestId("listen");
    //   expect(listenCards).toHaveLength(1);

    //   const removeListenButton = await within(listenCards[0]).findByLabelText(
    //     "Delete Listen"
    //   );
    //   expect(removeListenButton).toBeInTheDocument();
    //   await userEventSession.click(removeListenButton);
    //   await waitForElementToBeRemoved(listenCards);
    // });
  });
});
