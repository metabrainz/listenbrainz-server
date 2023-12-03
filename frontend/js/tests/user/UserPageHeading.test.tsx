import * as React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../test-utils/rtl-test-utils";
import UserPageHeading from "../../src/user/UserPageHeading";
import ReportUserButton from "../../src/report-user/ReportUser";
import APIService from "../../src/utils/APIService";

const user = {
  id: 1,
  name: "followed_user",
};

const loggedInUser = {
  id: 2,
  name: "iliekcomputers",
};

const userEventSession = userEvent.setup();
jest.unmock("react-toastify");

const testAPIService = new APIService("fnord");

describe("UserPageHeading", () => {
  it("renders the name of the user", async () => {
    render(
      <UserPageHeading
        user={user}
        loggedInUser={loggedInUser}
        loggedInUserFollowsUser
        alreadyReportedUser={false}
      />
    );
    const heading = await screen.findByRole("heading", { level: 2 });
    expect(heading).toHaveTextContent("followed_user");
  });

  it("does not render the FollowButton component if no loggedInUser", () => {
    // server sends an empty object in case no user is logged in
    render(
      <UserPageHeading
        user={user}
        loggedInUser={{} as ListenBrainzUser}
        loggedInUserFollowsUser={false}
        alreadyReportedUser={false}
      />
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("does not render the FollowButton component if the loggedInUser is looking at their own page", () => {
    render(
      <UserPageHeading
        user={user}
        loggedInUser={user}
        loggedInUserFollowsUser={false}
        alreadyReportedUser={false}
      />
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders the FollowButton component with the correct props if the loggedInUser and the user are different", async () => {
    render(
      <UserPageHeading
        user={user}
        loggedInUser={loggedInUser}
        loggedInUserFollowsUser={false}
        alreadyReportedUser={false}
      />
    );
    await screen.findByRole("button", { name: /Follow/ });
  });

  describe("ReportUser", () => {
    it("does not render a ReportUserButton nor ReportUserModal components if user is not logged in", () => {
      // server sends an empty object in case no user is logged in
      render(
        <UserPageHeading
          user={user}
          loggedInUser={{} as ListenBrainzUser}
          loggedInUserFollowsUser={false}
          alreadyReportedUser={false}
        />
      );

      expect(
        screen.queryByRole("button", { name: "Report User" })
      ).not.toBeInTheDocument();
    });

    it("renders the ReportUserButton and ReportUserModal components with the correct props inside the UserPageHeading", async () => {
      render(
        <UserPageHeading
          user={user}
          loggedInUser={loggedInUser}
          loggedInUserFollowsUser={false}
          alreadyReportedUser={false}
        />
      );

      await screen.findByRole("button", { name: "Report User" });
      await screen.findByRole("dialog");

      expect(
        screen.getByRole("heading", {
          name: /Report user/,
        })
      ).toHaveTextContent("Report user followed_user");
    });

    it("allows to report a user using the ReportUserModal", async () => {
      const apiCallSpy = jest.fn().mockImplementation(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: "followed_user has been reported successfully.",
            }),
        })
      );
      testAPIService.reportUser = apiCallSpy;

      renderWithProviders(
        <ReportUserButton user={user} alreadyReported={false} />,
        {
          APIService: testAPIService,
        }
      );

      //  Check initial state
      await screen.findByRole("button", {
        name: /Report User/,
      });
      await screen.findByRole("dialog");

      const textInput = await screen.findByRole("textbox");
      // Let's pretend we're writing in the textarea
      await userEventSession.type(textInput, "Can you see the Fnords?");

      // And then we click on the submit button
      const submitButton = await screen.findByRole("button", {
        name: /Report user/,
      });
      await userEventSession.click(submitButton);

      expect(apiCallSpy).toHaveBeenCalledWith(
        "followed_user",
        "Can you see the Fnords?"
      );

      await screen.findByRole("button", { name: /Report Submitted/ });
    });

    it("displays a user friendly message in the button text in case of error", async () => {
      const apiCallSpy = jest
        .fn()
        .mockImplementation(() =>
          Promise.reject(new Error("You cannot report yourself"))
        );

      testAPIService.reportUser = apiCallSpy;
      renderWithProviders(
        <ReportUserButton user={user} alreadyReported={false} />,
        {
          APIService: testAPIService,
        }
      );
      const reportUserButton = await screen.findByRole("button", {
        name: /Report User/,
      });
      const reportUserModal = await screen.findByRole("dialog");

      const submitButton = await screen.findByRole("button", {
        name: /Report user/,
      });

      await userEventSession.click(submitButton);

      expect(apiCallSpy).toHaveBeenCalledWith("followed_user", "");
      await screen.findByRole("button", { name: "Error! Try Again" });
    });
  });
});
