/*
 * listenbrainz-server - Server for the ListenBrainz project.
 *
 * Copyright (C) 2020 Param Singh <iliekcomputers@gmail.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

import * as React from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { isEmpty, isNil } from "lodash";
import NiceModal from "@ebay/nice-modal-react";
import FollowButton from "../follow/FollowButton";
import GlobalAppContext from "../utils/GlobalAppContext";
import ReportUserButton from "../report-user/ReportUser";
import { getPageProps } from "../utils/utils";

function UserPageHeading({
  user,
  loggedInUser,
  loggedInUserFollowsUser = false,
  alreadyReportedUser = false,
}: {
  user: ListenBrainzUser;
  loggedInUser?: ListenBrainzUser;
  loggedInUserFollowsUser: boolean;
  alreadyReportedUser: boolean;
}) {
  const hasLoggedInUser = !isNil(loggedInUser) && !isEmpty(loggedInUser);
  return (
    <>
      <h2 className="page-title">
        {user.name}
        {hasLoggedInUser && user.name !== loggedInUser?.name && (
          <FollowButton
            type="icon-only"
            user={user}
            loggedInUserFollowsUser={loggedInUserFollowsUser}
          />
        )}
      </h2>
      {hasLoggedInUser && user?.name !== loggedInUser?.name && (
        <ReportUserButton user={user} alreadyReported={alreadyReportedUser} />
      )}
    </>
  );
}

export default UserPageHeading;

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#user-page-heading-container");
  const { reactProps, globalAppContext, sentryProps } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }
  const {
    user,
    already_reported_user,
    logged_in_user_follows_user,
  } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <GlobalAppContext.Provider value={globalAppContext}>
      <NiceModal.Provider>
        <UserPageHeading
          user={user}
          loggedInUser={globalAppContext.currentUser || null}
          loggedInUserFollowsUser={logged_in_user_follows_user}
          alreadyReportedUser={already_reported_user}
        />
      </NiceModal.Provider>
    </GlobalAppContext.Provider>
  );
});
