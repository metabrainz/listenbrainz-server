import React from "react";

import { Navigate, Outlet, useLocation } from "react-router-dom";
import GlobalAppContext from "./GlobalAppContext";

function ProtectedRoutes() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const location = useLocation();
  const { pathname } = location;
  const urlEncodedPathname = encodeURIComponent(pathname);

  return currentUser?.name ? (
    <Outlet />
  ) : (
    <Navigate to={`/login/?next=${urlEncodedPathname}`} replace />
  );
}

export default ProtectedRoutes;
