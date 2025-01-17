import type { RouteObject } from "react-router-dom";
import RouteLoader, { RouteQueryLoader } from "../../../utils/Loader";

const getRecommendationsRoutes = (): RouteObject[] => {
  const routes = [
    {
      path: "/recommended/tracks/:userName/",
      lazy: async () => {
        const RecommendationsPageLayout = await import("../Layout");
        return { Component: RecommendationsPageLayout.default };
      },
      children: [
        {
          index: true,
          lazy: async () => {
            const Info = await import("../Info");
            return { Component: Info.default };
          },
          loader: RouteLoader,
        },
        {
          path: "raw/",
          lazy: async () => {
            const RecommendationsPage = await import("../Recommendations");
            return {
              Component: RecommendationsPage.default,
            };
          },
          loader: RouteQueryLoader("recommendation", true),
        },
      ],
    },
  ];
  return routes;
};

export default getRecommendationsRoutes;
