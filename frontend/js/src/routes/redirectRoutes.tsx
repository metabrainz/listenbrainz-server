import * as React from "react";
import { Navigate, Outlet } from "react-router";
import type { RouteObject } from "react-router";

const getRedirectRoutes = (): RouteObject[] => {
  const routes = [
    {
      path: "/",
      element: <Outlet />,
      children: [
        {
          path: "download/",
          element: <Navigate to="/data/" replace />,
        },
        {
          path: "similar-users/",
          element: <Navigate to="/explore/similar-users/" replace />,
        },
        {
          path: "huesound/",
          element: <Navigate to="/explore/huesound/" replace />,
        },
      ],
    },
  ];

  return routes;
};

export default getRedirectRoutes;
