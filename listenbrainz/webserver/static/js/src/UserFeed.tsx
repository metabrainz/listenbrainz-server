import * as React from "react";
import * as ReactDOM from "react-dom";
import ListenCard from "./listens/ListenCard";

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
          <div className="col-md-8">first column</div>
          <div className="col-md-4">second column</div>
        </div>
      </div>
    </>
  );
};

export default UserFeedPage;

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#react-container");
  ReactDOM.render(
    <UserFeedPage currentUser={{ id: 1, name: "iliekcomputers" }} />,
    domContainer
  );
});
