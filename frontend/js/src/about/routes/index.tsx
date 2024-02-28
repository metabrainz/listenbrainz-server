import RouteLoader from "../../utils/Loader";

const getAboutRoutes = () => {
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
          lazy: async () => {
            const About = await import("../About");
            return { Component: About.default };
          },
        },
        {
          path: "add-data/",
          lazy: async () => {
            const AddData = await import("../add-data/AddData");
            return { Component: AddData.default };
          },
        },
        {
          path: "current-status/",
          loader: RouteLoader,
          lazy: async () => {
            const CurrentStatus = await import(
              "../current-status/CurrentStatus"
            );
            return { Component: CurrentStatus.default };
          },
        },
        {
          path: "data/",
          lazy: async () => {
            const Data = await import("../data/Data");
            return { Component: Data.default };
          },
        },
        {
          path: "terms-of-service/",
          lazy: async () => {
            const TermsOfService = await import(
              "../terms-of-service/TermsOfService"
            );
            return { Component: TermsOfService.default };
          },
        },
      ],
    },
  ];
  return routes;
};

export default getAboutRoutes;
