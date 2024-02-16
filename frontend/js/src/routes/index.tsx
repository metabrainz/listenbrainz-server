import * as React from "react";
import { Outlet } from "react-router-dom";
import ImportData from "../import-data/ImportData";
import LastfmProxy from "../lastfm-proxy/LastfmProxy";
import ListensOffline from "../listens-offline/ListensOffline";
import MusicBrainzOffline from "../musicbrainz-offline/MusicBrainzOffline";
import SearchResults from "../search/UserSearch";
import MessyBrainz from "../messybrainz/MessyBrainz";
import RouteLoader from "../utils/Loader";
import { PlaylistPageWrapper } from "../playlists/Playlist";
import { PlayingNowPageWrapper } from "../metadata-viewer/MetadataViewerPage";
import UserEntityChart, {
  StatisticsChartLoader,
} from "../user/charts/UserEntityChart";
import { StatisticsPage } from "../user/stats/UserReports";
import UserDashboardLayout from "../user/layout";
import UserFeedPage from "../user-feed/UserFeed";
import {
  RecentListensLoader,
  RecentListensWrapper,
} from "../recent/RecentListens";
import UserFeedLayout from "../user-feed/UserFeedLayout";
import HomePage from "../home/Homepage";
import Login from "../login/Login";
import GDPR from "../gdpr/GDPR";

const getIndexRoutes = () => {
  const routes = [
    {
      path: "/",
      element: <Outlet />,
      children: [
        {
          index: true,
          element: <HomePage />,
          loader: RouteLoader,
        },
        {
          path: "login/",
          element: <Login />,
        },
        {
          path: "agree-to-terms/",
          element: <GDPR />,
        },
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
        {
          path: "playlist/:playlistID/",
          element: <PlaylistPageWrapper />,
          loader: RouteLoader,
        },
        {
          path: "listening-now/",
          element: <PlayingNowPageWrapper />,
          loader: RouteLoader,
        },
        {
          path: "/statistics/",
          element: <UserDashboardLayout />,
          children: [
            {
              index: true,
              element: <StatisticsPage />,
            },
            {
              path: "top-artists/",
              element: <UserEntityChart />,
              loader: StatisticsChartLoader,
            },
            {
              path: "top-albums/",
              element: <UserEntityChart />,
              loader: StatisticsChartLoader,
            },
            {
              path: "top-tracks/",
              element: <UserEntityChart />,
              loader: StatisticsChartLoader,
            },
          ],
        },
        {
          path: "/",
          element: <UserFeedLayout />,
          children: [
            {
              path: "/feed/",
              element: <UserFeedPage events={[]} />,
            },
            {
              path: "/recent/",
              element: <RecentListensWrapper />,
              loader: RecentListensLoader,
            },
          ],
        },
      ],
    },
  ];
  return routes;
};

export default getIndexRoutes;
