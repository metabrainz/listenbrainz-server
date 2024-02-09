import * as React from "react";
import { Outlet } from "react-router-dom";
import ImportData from "../import-data/ImportData";
import LastfmProxy from "../lastfm-proxy/LastfmProxy";
import ListensOffline from "../listens-offline/ListensOffline";
import MusicBrainzOffline from "../musicbrainz-offline/MusicBrainzOffline";
import SearchResults from "../search/UserSearch";
import MessyBrainz from "../messybrainz/MessyBrainz";
import RouteLoader from "../utils/Loader";

const getIndexRoutes = () => {
  const routes = [
    {
      path: "/",
      element: <Outlet />,
      children: [
        {
          path: "import-data/",
          element: <ImportData />,
        },
        {
          path: "messybrainz/",
          element: <MessyBrainz />,
        },
        {
          path: "lastfm-proxy/",
          element: <LastfmProxy />,
        },
        {
          path: "listens-offline/",
          element: <ListensOffline />,
        },
        {
          path: "musicbrainz-offline/",
          element: <MusicBrainzOffline />,
        },
        {
          path: "search/",
          element: <SearchResults />,
          loader: RouteLoader,
        },
      ],
    },
  ];
  return routes;
};

export default getIndexRoutes;
