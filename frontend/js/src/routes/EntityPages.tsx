import type { RouteObject } from "react-router-dom";
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
          lazy: async () => {
            const ArtistPage = await import("../artist/ArtistPage");
            return { Component: ArtistPage.default };
          },
          loader: RouteQueryLoader("artist"),
        },
        {
          path: "album/:albumMBID/",
          lazy: async () => {
            const AlbumPage = await import("../album/AlbumPage");
            return { Component: AlbumPage.default };
          },
          loader: RouteQueryLoader("album", undefined, (response: Response) => {
            // Don't throw an error on 404, allowing the isError state
            // in the AlbumPage query client state, to show custom error text
            return response?.status !== 404;
          }),
        },
        {
          path: "release-group/:releaseGroupMBID/",
          lazy: async () => {
            const ReleaseGroup = await import("../release-group/ReleaseGroup");
            return { Component: ReleaseGroup.default };
          },
        },
        {
          path: "release/:releaseMBID/",
          lazy: async () => {
            const Release = await import("../release/Release");
            return { Component: Release.default };
          },
          loader: RouteQueryLoader("release"),
        },
      ],
    },
  ];
  return routes;
};

export default getEntityPages;
