import React from "react";

import { Outlet, useLocation } from "react-router";
import GlobalAppContext from "./GlobalAppContext";
import buildAuthUrl from "./auth";

function ProtectedRoutes() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const location = useLocation();
  const { pathname } = location;

  if (!currentUser?.name) {
    // Redirect to Flask login route (not React Router)
    window.location.href = buildAuthUrl("login", pathname);
    return null;
  }

  return <Outlet />;
}

export default ProtectedRoutes;
