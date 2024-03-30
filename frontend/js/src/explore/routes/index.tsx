import * as React from "react";
import { Outlet } from "react-router-dom";
import RouteLoader from "../../utils/Loader";

const getExploreRoutes = () => {
  const routes = [
    {
      path: "/explore",
      lazy: async () => {
        const ExploreLayout = await import("../layout");
        return { Component: ExploreLayout.default };
      },
      children: [
        {
          index: true,
          lazy: async () => {
            const ExplorePage = await import("../Explore");
            return { Component: ExplorePage.default };
          },
        },
        {
          path: "art-creator/",
          lazy: async () => {
            const ArtCreator = await import("../art-creator/ArtCreator");
            return { Component: ArtCreator.default };
          },
        },
        {
          path: "cover-art-collage/",
          element: <Outlet />,
          children: [
            {
              index: true,
              lazy: async () => {
                const CoverArtComposite2023 = await import(
                  "../cover-art-collage/2023/CoverArtComposite"
                );

                return { Component: CoverArtComposite2023.default };
              },
            },
            {
              path: "2023/",
              lazy: async () => {
                const CoverArtComposite2023 = await import(
                  "../cover-art-collage/2023/CoverArtComposite"
                );

                return { Component: CoverArtComposite2023.default };
              },
            },
            {
              path: "2022/",
              lazy: async () => {
                const CoverArtComposite2022 = await import(
                  "../cover-art-collage/2022/CoverArtComposite"
                );

                return { Component: CoverArtComposite2022.default };
              },
            },
          ],
        },
        {
          path: "fresh-releases/",
          lazy: async () => {
            const FreshReleases = await import(
              "../fresh-releases/FreshReleases"
            );
            return { Component: FreshReleases.default };
          },
        },
        {
          path: "huesound/",
          lazy: async () => {
            const ColorPlay = await import("../huesound/ColorPlay");
            return { Component: ColorPlay.default };
          },
        },
        {
          path: "lb-radio/",
          lazy: async () => {
            const LBRadio = await import("../lb-radio/LBRadio");
            return { Component: LBRadio.default };
          },
          loader: RouteLoader,
        },
        {
          path: "similar-users/",
          lazy: async () => {
            const SimilarUsers = await import("../similar-users/SimilarUsers");
            return { Component: SimilarUsers.default };
          },
          loader: RouteLoader,
        },
        {
          path: "music-neighborhood/",
          lazy: async () => {
            const MusicNeighborhood = await import(
              "../music-neighborhood/MusicNeighborhood"
            );
            return { Component: MusicNeighborhood.default };
          },
          loader: RouteLoader,
        },
      ],
    },
  ];
  return routes;
};

export default getExploreRoutes;
