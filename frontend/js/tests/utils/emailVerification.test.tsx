import * as React from "react";
import { render, screen } from "@testing-library/react";
import {
  EMAIL_REQUIRED_BLOG_URL,
  EmailRequiredBlogLink,
  EmailVerificationRequiredAlert,
  EmailVerificationRequiredToastMessage,
  METABRAINZ_PROFILE_URL,
  MetaBrainzProfileLink,
} from "../../src/utils/emailVerification";

describe("emailVerification", () => {
  describe("MetaBrainzProfileLink", () => {
    it("points at the MetaBrainz profile page", () => {
      render(<MetaBrainzProfileLink />);
      const link = screen.getByRole("link", {
        name: "MetaBrainz profile page",
      });

      expect(link).toHaveAttribute("href", METABRAINZ_PROFILE_URL);
    });

    it("opens in a new tab without leaking the referrer", () => {
      // target="_blank" without rel="noreferrer" hands the destination a
      // window.opener reference, so both attributes belong together.
      render(<MetaBrainzProfileLink />);
      const link = screen.getByRole("link");

      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noreferrer");
    });
  });

  describe("EmailRequiredBlogLink", () => {
    it("points at the blog post explaining the requirement", () => {
      render(<EmailRequiredBlogLink />);
      const link = screen.getByRole("link", { name: "blog post" });

      expect(link).toHaveAttribute("href", EMAIL_REQUIRED_BLOG_URL);
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noreferrer");
    });
  });

  describe("EmailVerificationRequiredToastMessage", () => {
    it("names the action the user was attempting", () => {
      render(
        <EmailVerificationRequiredToastMessage action="pinning a track" />
      );

      expect(
        screen.getByText(/verify your email before pinning a track/)
      ).toBeInTheDocument();
    });

    it("offers the profile link as the way to resolve it", () => {
      render(<EmailVerificationRequiredToastMessage action="submitting" />);

      expect(
        screen.getByRole("link", { name: "MetaBrainz profile page" })
      ).toHaveAttribute("href", METABRAINZ_PROFILE_URL);
    });
  });

  describe("EmailVerificationRequiredAlert", () => {
    it("names the action the user was attempting", () => {
      render(<EmailVerificationRequiredAlert action="recommending a track" />);

      expect(
        screen.getByText(/verify an email address before recommending a track/)
      ).toBeInTheDocument();
    });

    it("renders as a danger alert", () => {
      render(<EmailVerificationRequiredAlert action="submitting" />);

      expect(
        screen.getByText(/You need to verify an email address before/)
      ).toHaveClass("alert", "alert-danger");
    });

    it("offers both the profile link and the explanation", () => {
      // The alert is the fuller form of the toast: it tells the user how to
      // fix it and why the email is needed at all.
      render(<EmailVerificationRequiredAlert action="submitting" />);

      expect(
        screen.getByRole("link", { name: "MetaBrainz profile page" })
      ).toHaveAttribute("href", METABRAINZ_PROFILE_URL);
      expect(screen.getByRole("link", { name: "blog post" })).toHaveAttribute(
        "href",
        EMAIL_REQUIRED_BLOG_URL
      );
    });
  });
});
