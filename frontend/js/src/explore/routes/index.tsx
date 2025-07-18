import * as React from "react";
import { Outlet } from "react-router";
import type { RouteObject } from "react-router";
import RouteLoader, { RouteQueryLoader } from "../../utils/Loader";

const getExploreRoutes = (): RouteObject[] => {
  const routes = [
    {
      path: "/explore",
      lazy: {
        Component: async () => {
          return (await import("../layout")).default;
        },
      },
      children: [
        {
          index: true,
          lazy: {
            Component: async () => {
              return (await import("../Explore")).default;
            },
          },
        },
        {
          path: "art-creator/",
          lazy: {
            Component: async () => {
              return (await import("../art-creator/ArtCreator")).default;
            },
          },
        },
        {
          path: "cover-art-collage/",
          element: <Outlet />,
          children: [
            {
              index: true,
              lazy: {
                Component: async () => {
                  return (
                    await import("../cover-art-collage/2023/CoverArtComposite")
                  ).default;
                },
              },
            },
            {
              path: "2023/",
              lazy: {
                Component: async () => {
                  return (
                    await import("../cover-art-collage/2023/CoverArtComposite")
                  ).default;
                },
              },
            },
            {
              path: "2022/",
              lazy: {
                Component: async () => {
                  return (
                    await import("../cover-art-collage/2022/CoverArtComposite")
                  ).default;
                },
              },
            },
          ],
        },
        {
          path: "fresh-releases/",
          lazy: {
            Component: async () => {
              return (await import("../fresh-releases/FreshReleases")).default;
            },
          },
        },
        {
          path: "huesound/:colorURLParam?",
          lazy: {
            Component: async () => {
              return (await import("../huesound/HueSound")).default;
            },
          },
        },
        {
          path: "lb-radio/",
          lazy: {
            Component: async () => {
              return (await import("../lb-radio/LBRadio")).default;
            },
            loader: async () => {
              return RouteLoader;
            },
          },
        },
        {
          path: "similar-users/",
          lazy: {
            Component: async () => {
              return (await import("../similar-users/SimilarUsers")).default;
            },
            loader: async () => {
              return RouteQueryLoader("similar-users");
            },
          },
        },
        {
          path: "music-neighborhood/",
          lazy: {
            Component: async () => {
              return (await import("../music-neighborhood/MusicNeighborhood"))
                .default;
            },
            loader: async () => {
              return RouteQueryLoader("music-neighborhood");
            },
          },
        },
        {
          path: "ai-brainz/",
          lazy: {
            Component: async () => {
              return (await import("../ai-brainz/AIBrainz")).default;
            },
          },
        },
        {
          path: "genre-explorer/:genreMBID",
          lazy: async () => {
            const GenreExplorer = await import(
              "../genre-explorer/GenreExplorer"
            );
            return { Component: GenreExplorer.default };
          },
          loader: RouteQueryLoader("genre-explorer"),
        },
      ],
    },
  ];
  return routes;
};

export default getExploreRoutes;
