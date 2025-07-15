import * as React from "react";
import { Navigate, Outlet } from "react-router";
import type { RouteObject } from "react-router";

const getRedirectRoutes = (): RouteObject[] => {
  const routes = [
    {
      path: "/profile",
      element: <Outlet />,
      children: [
        {
          index: true,
          element: <Navigate to="/settings/" replace />,
        },
        {
          path: "resettoken/",
          element: <Navigate to="/settings/resettoken/" replace />,
        },
        {
          path: "music-services/details/",
          element: <Navigate to="/settings/music-services/details/" replace />,
        },
        {
          path: "link-listens/",
          element: <Navigate to="/settings/link-listens/" replace />,
        },
        {
          path: "select_timezone/",
          element: <Navigate to="/settings/select_timezone/" replace />,
        },
        {
          path: "troi/",
          element: <Navigate to="/settings/troi/" replace />,
        },
        {
          path: "export/",
          element: <Navigate to="/settings/export/" replace />,
        },
        {
          path: "delete-listens/",
          element: <Navigate to="/settings/delete-listens/" replace />,
        },
        {
          path: "delete/",
          element: <Navigate to="/settings/delete/" replace />,
        },
      ],
    },
  ];

  return routes;
};

export default getRedirectRoutes;
