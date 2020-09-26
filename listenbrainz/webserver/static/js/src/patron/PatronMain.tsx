import * as React from "react";
import * as ReactDOM from "react-dom";
import PatronPaymentButtons from "./PatronPaymentButtons";
import PatronList from "./PatronList";

const PatronPage = ({ successful = false }: { successful: boolean }) => {
  return (
    <>
      {successful && <div className="alert">hello!</div>}
      <h1 style={{ textAlign: "center" }}>Become a ListenBrainz patron!</h1>
      <h3 style={{ textAlign: "center" }}>
        No ads, no subscriptions; but open-source and passion.
      </h3>
      <hr />
      <PatronPaymentButtons />
      <hr />
      <div role="main" style={{ marginLeft: "15%", marginRight: "15%" }}>
        <h4 style={{ textAlign: "center" }}>
          We are a non‑profit organization because we believe in free, open
          access to data.
        </h4>
        <h4 style={{ textAlign: "center" }}>
          We rely on support from people like you to make it possible. If you
          enjoy ListenBrainz, please consider supporting us by donating and
          becoming a Patron!
        </h4>
      </div>

      <br />
      <div className="row">
        <h4 style={{ textAlign: "center", fontStyle: "italic" }}>
          We are a small team, so your support makes a huge difference!
        </h4>
      </div>
      <hr />
      <div className="row">
        <h3 style={{ textAlign: "center" }}>
          The Patrons who make ListenBrainz possible
        </h3>
        <br />
      </div>
      <PatronList patrons={["param", "singh", "bruh", "hello", "world"]} />
    </>
  );
};

export default PatronPage;

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#react-container");
  ReactDOM.render(<PatronPage successful={false} />, domContainer);
});
