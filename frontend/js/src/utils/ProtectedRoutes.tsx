import React from "react";

import { Navigate, Outlet } from "react-router-dom";
import GlobalAppContext from "./GlobalAppContext";
import Layout from "../layout";

function ProtectedRoutes() {
  const { currentUser } = React.useContext(GlobalAppContext);

  return currentUser?.name ? <Layout /> : <Navigate to="/login" replace />;
}

export default ProtectedRoutes;
