import * as React from "react";
import * as ReactDOM from "react-dom";

import PatronPage from "./PatronMain";

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#react-container");
  ReactDOM.render(<PatronPage successful />, domContainer);
});
