import RouteLoader from "../utils/Loader";

const getEntityPages = () => {
  const routes = [
    {
      path: "/",
      lazy: async () => {
        const EntityPageLayout = await import("../layout/EntityPages");
        return { Component: EntityPageLayout.default };
      },
      children: [
        {
          path: "artist/:artistMBID/",
          lazy: async () => {
            const ArtistPage = await import("../artist/ArtistPage");
            return { Component: ArtistPage.default };
          },
          loader: RouteLoader,
        },
        {
          path: "album/:albumMBID/",
          lazy: async () => {
            const AlbumPage = await import("../album/AlbumPage");
            return { Component: AlbumPage.default };
          },
          loader: RouteLoader,
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
          loader: RouteLoader,
        },
      ],
    },
  ];
  return routes;
};

export default getEntityPages;
