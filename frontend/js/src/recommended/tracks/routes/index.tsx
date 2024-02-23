import * as React from "react";

import RecommendationsPageLayout from "../Layout";
import Info from "../Info";
import { RecommendationsPageWrapper } from "../Recommendations";
import RouteLoader from "../../../utils/Loader";

const getRecommendationsRoutes = () => {
  const routes = [
    {
      path: "/recommended/tracks/:userName/",
      element: <RecommendationsPageLayout />,
      children: [
        {
          index: true,
          element: <Info />,
          loader: RouteLoader,
        },
        {
          path: "raw/",
          element: <RecommendationsPageWrapper />,
          loader: RouteLoader,
        },
      ],
    },
  ];
  return routes;
};

export default getRecommendationsRoutes;
