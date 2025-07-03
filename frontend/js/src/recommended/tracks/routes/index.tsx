import type { RouteObject } from "react-router";
import RouteLoader, { RouteQueryLoader } from "../../../utils/Loader";

const getRecommendationsRoutes = (): RouteObject[] => {
  const routes = [
    {
      path: "/recommended/tracks/:userName/",
      lazy: {
        Component: async () => {
          return (await import("../Layout")).default;
        },
      },
      children: [
        {
          index: true,
          lazy: {
            Component: async () => {
              return (await import("../Info")).default;
            },
            loader: async () => {
              return RouteLoader;
            },
          },
        },
        {
          path: "raw/",
          lazy: {
            Component: async () => {
              return (await import("../Recommendations")).default;
            },
            loader: async () => {
              return RouteQueryLoader("recommendation", true);
            },
          },
        },
      ],
    },
  ];
  return routes;
};

export default getRecommendationsRoutes;
