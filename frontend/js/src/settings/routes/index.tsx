import * as React from "react";
import RouteLoader from "../../utils/Loader";
import ErrorBoundary from "../../error/ErrorBoundary";

const getSettingsRoutes = () => {
  const routes = [
    {
      path: "/settings",
      lazy: async () => {
        const SettingsLayout = await import("../layout");
        return { Component: SettingsLayout.default };
      },
      errorElement: <ErrorBoundary />,
      children: [
        {
          index: true,
          lazy: async () => {
            const Settings = await import("../Settings");
            return { Component: Settings.default };
          },
        },
        {
          path: "resettoken/",
          lazy: async () => {
            const ResetToken = await import("../resettoken/ResetToken");
            return { Component: ResetToken.default };
          },
        },
        {
          path: "music-services/details/",
          loader: RouteLoader,
          lazy: async () => {
            const MusicServices = await import(
              "../music-services/details/MusicServices"
            );
            return { Component: MusicServices.default };
          },
        },
        {
          path: "brainzplayer/",
          lazy: async () => {
            const BrainzPlayerSettings = await import(
              "../brainzplayer/BrainzPlayerSettings"
            );
            return { Component: BrainzPlayerSettings.default };
          },
        },
        {
          path: "import/",
          loader: RouteLoader,
          lazy: async () => {
            const Import = await import("../import/ImportListens");
            return { Component: Import.default };
          },
        },
        {
          path: "resetlatestimportts/",
          lazy: async () => {
            const ResetImportTimestamp = await import(
              "../resetlatestimportts/ResetLatestImports"
            );
            return { Component: ResetImportTimestamp.default };
          },
        },
        {
          path: "missing-data/",
          loader: RouteLoader,
          lazy: async () => {
            const MissingMBData = await import("../missing-data/MissingMBData");
            return { Component: MissingMBData.MissingMBDataPageWrapper };
          },
        },
        {
          path: "select_timezone/",
          loader: RouteLoader,
          lazy: async () => {
            const SelectTimezone = await import(
              "../select_timezone/SelectTimezone"
            );
            return { Component: SelectTimezone.SelectTimezoneWrapper };
          },
        },
        {
          path: "troi/",
          loader: RouteLoader,
          lazy: async () => {
            const SelectTroiPreferences = await import(
              "../troi/SelectTroiPreferences"
            );
            return {
              Component: SelectTroiPreferences.SelectTroiPreferencesWrapper,
            };
          },
        },
        {
          path: "export/",
          lazy: async () => {
            const Export = await import("../export/ExportData");
            return { Component: Export.default };
          },
        },
        {
          path: "delete-listens/",
          lazy: async () => {
            const DeleteListens = await import(
              "../delete-listens/DeleteListens"
            );
            return { Component: DeleteListens.default };
          },
        },
        {
          path: "delete/",
          lazy: async () => {
            const DeleteAccount = await import("../delete/DeleteAccount");
            return { Component: DeleteAccount.default };
          },
        },
      ],
    },
  ];
  return routes;
};

export default getSettingsRoutes;
