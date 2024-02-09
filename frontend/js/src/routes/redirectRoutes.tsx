import * as React from "react";
import { Navigate, Outlet, Params } from "react-router-dom";

const getRedirectRoutes = () => {
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
        {
          path: "import/",
          element: <Navigate to="/settings/import/" replace />,
        },
      ],
    },
  ];

  return routes;
};

export default getRedirectRoutes;
