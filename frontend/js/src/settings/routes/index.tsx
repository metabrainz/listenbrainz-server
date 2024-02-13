import * as React from "react";
import SettingsLayout from "../layout";
import DeleteAccount from "../delete/DeleteAccount";
import DeleteListens from "../delete-listens/DeleteListens";
import Export from "../export/ExportData";
import Import from "../import/ImportListens";
import { MissingMBDataPageWrapper as MissingMBDataPage } from "../missing-data/MissingMBData";
import MusicServices from "../music-services/details/MusicServices";
import ResetToken from "../resettoken/ResetToken";
import { SelectTimezoneWrapper as SelectTimezone } from "../select_timezone/SelectTimezone";
import { SelectTroiPreferencesWrapper as SelectTroiPreferences } from "../troi/SelectTroiPreferences";
import Settings from "../Settings";
import ResetImportTimestamp from "../resetlatestimportts/ResetLatestImports";
import RouteLoader from "../../utils/Loader";
import ErrorBoundary from "../../error/ErrorBoundary";

const getSettingsRoutes = () => {
  const routes = [
    {
      path: "/settings",
      element: <SettingsLayout />,
      errorElement: <ErrorBoundary />,
      children: [
        {
          index: true,
          element: <Settings />,
        },
        {
          path: "resettoken/",
          element: <ResetToken />,
        },
        {
          path: "music-services/details/",
          loader: RouteLoader,
          element: <MusicServices />,
        },
        {
          path: "import/",
          loader: RouteLoader,
          element: <Import />,
        },
        {
          path: "resetlatestimportts/",
          element: <ResetImportTimestamp />,
        },
        {
          path: "missing-data/",
          loader: RouteLoader,
          element: <MissingMBDataPage />,
        },
        {
          path: "select_timezone/",
          loader: RouteLoader,
          element: <SelectTimezone />,
        },
        {
          path: "troi/",
          loader: RouteLoader,
          element: <SelectTroiPreferences />,
        },
        {
          path: "export/",
          element: <Export />,
        },
        {
          path: "delete-listens/",
          element: <DeleteListens />,
        },
        {
          path: "delete/",
          element: <DeleteAccount />,
        },
      ],
    },
  ];
  return routes;
};

export default getSettingsRoutes;
