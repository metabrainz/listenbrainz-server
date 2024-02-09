import * as React from "react";
import EntityPageLayout from "../layout/EntityPages";
import ArtistPage from "../artist/ArtistPage";
import AlbumPage from "../album/AlbumPage";
import RouteLoader from "../utils/Loader";
import ReleaseGroup from "../release-group/ReleaseGroup";
import Release from "../release/Release";

const getEntityPages = () => {
  const routes = [
    {
      path: "/",
      element: <EntityPageLayout />,
      children: [
        {
          path: "artist/:artistMBID/",
          element: <ArtistPage />,
          loader: RouteLoader,
        },
        {
          path: "album/:albumMBID/",
          element: <AlbumPage />,
          loader: RouteLoader,
        },
        {
          path: "release-group/:releaseGroupMBID/",
          element: <ReleaseGroup />,
        },
        {
          path: "release/:releaseMBID/",
          element: <Release />,
          loader: RouteLoader,
        },
      ],
    },
  ];
  return routes;
};

export default getEntityPages;
