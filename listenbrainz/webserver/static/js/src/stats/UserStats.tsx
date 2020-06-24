import * as ReactDOM from "react-dom";
import * as React from "react";

import ErrorBoundary from "../ErrorBoundary";
import Card from "../components/Card";

export type UserStatsProps = {
  user: ListenBrainzUser;
  apiUrl: string;
};

class UserStats extends React.Component<UserStatsProps> {
  render() {
    return (
      <div style={{ marginTop: "1em" }}>
        <div className="row">
          <Card>
            <h2>Hello</h2>
          </Card>
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
