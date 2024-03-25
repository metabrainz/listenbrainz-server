import * as React from "react";
import { Navigate, Outlet, Params } from "react-router-dom";

const getRedirectRoutes = () => {
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
          path: "import/",
          element: <Navigate to="/settings/import/" replace />,
        },
        {
          path: "resetlatestimportts/",
          element: <Navigate to="/settings/resetlatestimportts/" replace />,
        },
        {
          path: "missing-data/",
          element: <Navigate to="/settings/missing-data/" replace />,
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
