import type { RouteObject } from "react-router";
import { RouteQueryLoader } from "../../utils/Loader";

const getAboutRoutes = (): RouteObject[] => {
  const routes = [
    {
      path: "/",
      lazy: async () => {
        const AboutLayout = await import("../layout");
        return { Component: AboutLayout.default };
      },
      children: [
        {
          path: "about/",
          lazy: {
            Component: async () => {
              return (await import("../About")).default;
            },
          },
        },
        {
          path: "add-data/",
          lazy: {
            Component: async () => {
              return (await import("../add-data/AddData")).default;
            },
          },
        },
        {
          path: "current-status/",
          lazy: {
            Component: async () => {
              return (await import("../current-status/CurrentStatus")).default;
            },
            loader: async () => {
              return RouteQueryLoader("current-status");
            },
          },
        },
        {
          path: "data/",
          lazy: {
            Component: async () => {
              return (await import("../data/Data")).default;
            },
          },
        },
        {
          path: "terms-of-service/",
          lazy: {
            Component: async () => {
              return (await import("../terms-of-service/TermsOfService"))
                .default;
            },
          },
        },
      ],
    },
    {
      path: "donate/",
      lazy: {
        Component: async () => {
          return (await import("../donations/Donate")).default;
        },
      },
    },
  ];
  return routes;
};

export default getAboutRoutes;
