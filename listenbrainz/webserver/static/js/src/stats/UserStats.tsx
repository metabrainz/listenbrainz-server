import * as ReactDOM from "react-dom";
import * as React from "react";

import ErrorBoundary from "../ErrorBoundary";
import Pill from "../components/Pill";
import UserListeningActivity from "./UserListeningActivity";

export type UserStatsProps = {
  user: ListenBrainzUser;
  apiUrl: string;
};

class UserStats extends React.Component<UserStatsProps> {
  render() {
    return (
      <div style={{ marginTop: "1em" }}>
        <div className="row">
          <div className="col-xs-12">
            <Pill active type="secondary">
              Week
            </Pill>
            <Pill type="secondary">Month</Pill>
            <Pill type="secondary">Year</Pill>
            <Pill type="secondary">All Time</Pill>
          </div>
        </div>
        <div className="row">
          <UserListeningActivity />
        </div>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#react-container");
  const propsElement = document.getElementById("react-props");
  let reactProps;
  try {
    reactProps = JSON.parse(propsElement!.innerHTML);
  } catch (err) {
    // Show error to the user and ask to reload page
  }
  const { user, api_url: apiUrl } = reactProps;
  ReactDOM.render(
    <ErrorBoundary>
      <UserStats apiUrl={apiUrl} user={user} />
    </ErrorBoundary>,
    domContainer
  );
});
