import * as React from "react";
import { Navigate, Outlet } from "react-router-dom";
import type { RouteObject } from "react-router-dom";

const getRedirectRoutes = (musicbrainzID?: string): RouteObject[] => {
  // Handle redirects if the user is not logged in
  if (!musicbrainzID) {
    return [];
  }

  const routes = [
    {
      path: "/my/",
      element: <Outlet />,
      children: [
        {
          path: "listens/",
          element: <Navigate to={`/user/${musicbrainzID}/`} replace />,
        },
        {
          path: "stats/",
          element: <Navigate to={`/user/${musicbrainzID}/stats/`} replace />,
        },
        {
          path: "playlists/",
          element: (
            <Navigate to={`/user/${musicbrainzID}/playlists/`} replace />
          ),
        },
        {
          path: "recommendations/",
          element: (
            <Navigate to={`/user/${musicbrainzID}/recommendations/`} replace />
          ),
        },
        {
          path: "redirect_recommendations/",
          element: (
            <Navigate to={`/user/${musicbrainzID}/recommendations/`} replace />
          ),
        },
        {
          path: "taste/",
          element: <Navigate to={`/user/${musicbrainzID}/taste/`} replace />,
        },
        {
          path: "year-in-music/",
          element: (
            <Navigate to={`/user/${musicbrainzID}/year-in-music/`} replace />
          ),
        },
      ],
    },
  ];

  return routes;
};

export default getRedirectRoutes;
