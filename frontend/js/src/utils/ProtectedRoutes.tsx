import React from "react";

import { Navigate, useLocation } from "react-router-dom";
import GlobalAppContext from "./GlobalAppContext";

function ProtectedRoutes() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const location = useLocation();
  const { pathname } = location;
  const urlEncodedPathname = encodeURIComponent(pathname);

  return currentUser?.name ? (
    <div />
  ) : (
    <Navigate to={`/login/?next=${urlEncodedPathname}`} />
  );
}

export default ProtectedRoutes;
