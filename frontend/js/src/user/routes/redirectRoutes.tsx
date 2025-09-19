import * as React from "react";
import { Navigate, Outlet } from "react-router";
import type { RouteObject } from "react-router";

const getRedirectRoutes = (musicbrainzID?: string): RouteObject[] => {
  // Handle redirects if the user is not logged in
  if (!musicbrainzID) {
    return [];
  }
  const encodedMusicBrainzID = encodeURIComponent(musicbrainzID);

  const routes = [
    {
      path: "/my/",
      element: <Outlet />,
      children: [
        {
          path: "listens/",
          element: <Navigate to={`/user/${encodedMusicBrainzID}/`} replace />,
        },
        {
          path: "stats/",
          element: (
            <Navigate to={`/user/${encodedMusicBrainzID}/stats/`} replace />
          ),
        },
        {
          path: "playlists/",
          element: (
            <Navigate to={`/user/${encodedMusicBrainzID}/playlists/`} replace />
          ),
        },
        {
          path: "recommendations/",
          element: (
            <Navigate
              to={`/user/${encodedMusicBrainzID}/recommendations/`}
              replace
            />
          ),
        },
        {
          path: "redirect_recommendations/",
          element: (
            <Navigate
              to={`/user/${encodedMusicBrainzID}/recommendations/`}
              replace
            />
          ),
        },
        {
          path: "taste/",
          element: (
            <Navigate to={`/user/${encodedMusicBrainzID}/taste/`} replace />
          ),
        },
        {
          path: "year-in-music/",
          element: (
            <Navigate
              to={`/user/${encodedMusicBrainzID}/year-in-music/`}
              replace
            />
          ),
        },
      ],
    },
  ];

  return routes;
};

export default getRedirectRoutes;
