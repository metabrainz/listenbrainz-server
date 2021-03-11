import * as React from "react";
import * as ReactDOM from "react-dom";
import UserSocialNetwork from "./follow/UserSocialNetwork";

type UserFeedPageProps = {
  currentUser: ListenBrainzUser;
};

const UserFeedPage = (props: UserFeedPageProps) => {
  const { currentUser } = props;
  return (
    <>
      <h2>Feed - {currentUser.name}</h2>
      <div role="main">
        <div className="row">
          <div className="col-md-8">
            <div className="alert alert-danger">Under construction!</div>
          </div>
          <div className="col-md-4">
            <UserSocialNetwork user={currentUser} loggedInUser={currentUser} />
          </div>
        </div>
      </div>
    </>
  );
};

export default UserFeedPage;

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#react-container");
  const propsElement = document.getElementById("react-props");
  const reactProps = JSON.parse(propsElement!.innerHTML);
  ReactDOM.render(
    <UserFeedPage currentUser={reactProps.current_user} />,
    domContainer
  );
});
