import * as React from "react";
import { Outlet, ScrollRestoration } from "react-router-dom";

import Footer from "../components/Footer";
import Navbar from "../components/Navbar";

export default function Layout() {
  return (
    <>
      <ScrollRestoration />
      <Navbar />
      <div className="container-react">
        <div className="container-react-main">
          <Outlet />
        </div>
        <Footer />
      </div>
    </>
  );
}
