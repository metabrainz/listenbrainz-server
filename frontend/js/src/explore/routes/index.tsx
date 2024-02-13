import * as React from "react";
import { Outlet } from "react-router-dom";
import ExploreLayout from "../layout";
import ExplorePage from "../Explore";
import ColorPlay from "../huesound/ColorPlay";
import ArtCreator from "../art-creator/ArtCreator";
import CoverArtComposite2023 from "../cover-art-collage/2023/CoverArtComposite";
import CoverArtComposite2022 from "../cover-art-collage/2022/CoverArtComposite";
import FreshReleases from "../fresh-releases/FreshReleases";
import LBRadio from "../lb-radio/LBRadio";
import SimilarUsers from "../similar-users/SimilarUsers";
import MusicNeighborhood from "../music-neighborhood/MusicNeighborhood";
import RouteLoader from "../../utils/Loader";

const getExploreRoutes = () => {
  const routes = [
    {
      path: "/explore",
      element: <ExploreLayout />,
      children: [
        {
          index: true,
          element: <ExplorePage />,
        },
        {
          path: "art-creator/",
          element: <ArtCreator />,
        },
        {
          path: "cover-art-collage/",
          element: <Outlet />,
          children: [
            {
              index: true,
              element: <CoverArtComposite2023 />,
            },
            {
              path: "2023/",
              element: <CoverArtComposite2023 />,
            },
            {
              path: "2022/",
              element: <CoverArtComposite2022 />,
            },
          ],
        },
        {
          path: "fresh-releases/",
          element: <FreshReleases />,
        },
        {
          path: "huesound/",
          element: <ColorPlay />,
        },
        {
          path: "lb-radio/",
          element: <LBRadio />,
          loader: RouteLoader,
        },
        {
          path: "similar-users/",
          element: <SimilarUsers />,
          loader: RouteLoader,
        },
        {
          path: "music-neighborhood/",
          element: <MusicNeighborhood />,
          loader: RouteLoader,
        },
      ],
    },
  ];
  return routes;
};

export default getExploreRoutes;
