import * as React from "react";
import { Outlet } from "react-router-dom";
import type { RouteObject } from "react-router-dom";
import RouteLoader, { RouteQueryLoader } from "../../utils/Loader";

const getExploreRoutes = (): RouteObject[] => {
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
          path: "huesound/:colorURLParam?",
          lazy: async () => {
            const HueSound = await import("../huesound/HueSound");
            return { Component: HueSound.default };
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
          loader: RouteQueryLoader("similar-users"),
        },
        {
          path: "music-neighborhood/",
          lazy: async () => {
            const MusicNeighborhood = await import(
              "../music-neighborhood/MusicNeighborhood"
            );
            return { Component: MusicNeighborhood.default };
          },
          loader: RouteQueryLoader("music-neighborhood"),
        },
        {
          path: "ai-brainz/",
          lazy: async () => {
            const AIBrainzComponent = await import("../ai-brainz/AIBrainz");
            return { Component: AIBrainzComponent.default };
          },
        },
      ],
    },
  ];
  return routes;
};

export default getExploreRoutes;
