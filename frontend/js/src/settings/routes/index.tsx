import * as React from "react";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import SettingsLayout from "../layout";
import DeleteAccount from "../delete/DeleteAccount";
import DeleteListens from "../delete-listens/DeleteListens";
import Export from "../export/ExportData";
import Import, { ImportLoader } from "../import/ImportListens";
import {
  MissingMBDataPageLoader,
  MissingMBDataPageWrapper,
} from "../missing-data/MissingMBData";
import MusicServices, {
  MusicServicesLoader,
} from "../music-services/details/MusicServices";
import ResetToken from "../resettoken/ResetToken";
import {
  SelectTimezoneLoader,
  SelectTimezoneWrapper,
} from "../select_timezone/SelectTimezone";
import {
  SelectTroiPreferencesLoader,
  SelectTroiPreferencesWrapper,
} from "../troi/SelectTroiPreferences";
import Settings from "../Settings";
import ResetImportTimestamp from "../resetlatestimportts/ResetLatestImports";

const getSettingsRoutes = () => {
  const SettingsWithAlertNotifications = withAlertNotifications(Settings);
  const ResetTokenWithAlertNotifications = withAlertNotifications(ResetToken);
  const MusicServicesWithAlertNotifications = withAlertNotifications(
    MusicServices
  );
  const ImportWithAlertNotifications = withAlertNotifications(Import);
  const ResetImportTimestampWithAlertNotifications = withAlertNotifications(
    ResetImportTimestamp
  );
  const SelectTroiPreferencesWithAlertNotifications = withAlertNotifications(
    SelectTroiPreferencesWrapper
  );
  const MissingMBDataPageWithAlertNotification = withAlertNotifications(
    MissingMBDataPageWrapper
  );
  const SelectTimezoneWithAlertNotifications = withAlertNotifications(
    SelectTimezoneWrapper
  );

  const ExportWithAlertNotifications = withAlertNotifications(Export);
  const DeleteListensWithAlertNotifications = withAlertNotifications(
    DeleteListens
  );
  const DeleteAccountWithAlertNotifications = withAlertNotifications(
    DeleteAccount
  );

  const routes = [
    {
      path: "/profile",
      element: <SettingsLayout />,
      children: [
        {
          index: true,
          element: <SettingsWithAlertNotifications />,
        },
        {
          path: "resettoken/",
          element: <ResetTokenWithAlertNotifications />,
        },
        {
          path: "music-services/details/",
          loader: MusicServicesLoader,
          element: <MusicServicesWithAlertNotifications />,
        },
        {
          path: "import/",
          loader: ImportLoader,
          element: <ImportWithAlertNotifications />,
        },
        {
          path: "resetlatestimportts/",
          element: <ResetImportTimestampWithAlertNotifications />,
        },
        {
          path: "missing-data/",
          loader: MissingMBDataPageLoader,
          element: <MissingMBDataPageWithAlertNotification />,
        },
        {
          path: "select_timezone/",
          loader: SelectTimezoneLoader,
          element: <SelectTimezoneWithAlertNotifications />,
        },
        {
          path: "troi/",
          loader: SelectTroiPreferencesLoader,
          element: <SelectTroiPreferencesWithAlertNotifications />,
        },
        {
          path: "export/",
          element: <ExportWithAlertNotifications />,
        },
        {
          path: "delete-listens/",
          element: <DeleteListensWithAlertNotifications />,
        },
        {
          path: "delete/",
          element: <DeleteAccountWithAlertNotifications />,
        },
      ],
    },
  ];
  return routes;
};

export default getSettingsRoutes;
