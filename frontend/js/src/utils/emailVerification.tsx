import * as React from "react";

export const METABRAINZ_PROFILE_URL = "https://metabrainz.org/profile";
export const EMAIL_REQUIRED_BLOG_URL = "https://blog.metabrainz.org/?p=8915";

export function MetaBrainzProfileLink() {
  return (
    <a href={METABRAINZ_PROFILE_URL} target="_blank" rel="noreferrer">
      MetaBrainz profile page
    </a>
  );
}

export function EmailRequiredBlogLink() {
  return (
    <a href={EMAIL_REQUIRED_BLOG_URL} target="_blank" rel="noreferrer">
      blog post
    </a>
  );
}

type EmailVerificationRequiredToastMessageProps = {
  action: string;
};

export function EmailVerificationRequiredToastMessage({
  action,
}: EmailVerificationRequiredToastMessageProps) {
  return (
    <>
      Please check your inbox for a verification email, or go to your{" "}
      <MetaBrainzProfileLink /> to verify your email before {action}.
    </>
  );
}

type EmailVerificationRequiredAlertProps = {
  action: string;
};

export function EmailVerificationRequiredAlert({
  action,
}: EmailVerificationRequiredAlertProps) {
  return (
    <div className="alert alert-danger">
      You need to verify an email address before {action}. Please check your
      inbox for a verification email, or go to your <MetaBrainzProfileLink /> to
      verify your email. Read this{" "}
      <EmailRequiredBlogLink /> to understand why we need your email.
    </div>
  );
}
