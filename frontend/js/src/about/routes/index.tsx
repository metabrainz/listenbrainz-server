import * as React from "react";
import AboutLayout from "../layout";
import About from "../About";
import AddData from "../add-data/AddData";
import CurrentStatus, {
  CurrentStatusLoader,
} from "../current-status/CurrentStatus";
import Data from "../data/Data";
import TermsOfService from "../terms-of-service/TermsOfService";

const getAboutRoutes = () => {
  const routes = [
    {
      path: "/",
      element: <AboutLayout />,
      children: [
        {
          path: "about/",
          element: <About />,
        },
        {
          path: "add-data/",
          element: <AddData />,
        },
        {
          path: "current-status/",
          loader: CurrentStatusLoader,
          element: <CurrentStatus />,
        },
        {
          path: "data/",
          element: <Data />,
        },
        {
          path: "terms-of-service/",
          element: <TermsOfService />,
        },
      ],
    },
  ];
  return routes;
};

export default getAboutRoutes;
