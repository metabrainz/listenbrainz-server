import * as React from "react";
import * as ReactDOM from "react-dom";

const FollowButton = (currentUser: any) => {
  // this renders the logged-in user's name right now, should render the name of the user whose
  // profile it is
  return (
    <>
      <h2 className="page-title">{currentUser.name}</h2>
      <span>Yo yo, pammu</span>
    </>
  );
};

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#follow-controls-container");

  const propsElement = document.getElementById("react-props");
  const reactProps = JSON.parse(propsElement!.innerHTML);
  const { current_user } = reactProps;
  ReactDOM.render(<FollowButton currentUser={current_user} />, domContainer);
});
