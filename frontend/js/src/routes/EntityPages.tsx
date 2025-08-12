import type { RouteObject } from "react-router";
import { RouteQueryLoader } from "../utils/Loader";

const getEntityPages = (): RouteObject[] => {
  const routes = [
    {
      path: "/",
      lazy: async () => {
        const EntityPageLayout = await import("../layout/LayoutWithBackButton");
        return { Component: EntityPageLayout.default };
      },
      children: [
        {
          path: "artist/:artistMBID/",
          lazy: {
            Component: async () => {
              return (await import("../artist/ArtistPage")).default;
            },
            loader: async () => {
              return RouteQueryLoader("artist");
            },
          },
        },
        {
          path: "album/:albumMBID/",
          lazy: {
            Component: async () => {
              return (await import("../album/AlbumPage")).default;
            },
            loader: async () => {
              return RouteQueryLoader(
                "album",
                undefined,
                (response: Response) => {
                  // Don't throw an error on 404, allowing the isError state
                  // in the AlbumPage query client state, to show custom error text
                  return response?.status !== 404;
                }
              );
            },
          },
        },
        {
          path: "release-group/:releaseGroupMBID/",
          lazy: {
            Component: async () => {
              return (await import("../release-group/ReleaseGroup")).default;
            },
          },
        },
        {
          path: "release/:releaseMBID/",
          lazy: {
            Component: async () => {
              return (await import("../release/Release")).default;
            },
            loader: async () => {
              return RouteQueryLoader("release");
            },
          },
        },
        {
          path: "track/:trackMBID/",
          lazy: {
            Component: async () => {
              return (await import("../track/Track")).default;
            },
            loader: async () => {
              return RouteQueryLoader("track");
            },
          },
        },
        {
          path: "recording/:recordingMBID/",
          lazy: {
            Component: async () => {
              return (await import("../recording/Recording")).default;
            },
          },
        },
      ],
    },
  ];
  return routes;
};

export default getEntityPages;
