import * as React from "react";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import SettingsLayout from "../layout";
import DeleteAccount from "../pages/DeleteAccount";
import DeleteListens from "../pages/DeleteListens";
import Export from "../pages/ExportData";
import Import, { ImportLoader } from "../pages/ImportListens";
import MusicServices, { MusicServicesLoader } from "../pages/MusicServices";
import ResetToken from "../pages/ResetToken";
import {
  SelectTimezoneLoader,
  SelectTimezoneWrapper,
} from "../pages/SelectTimezone";
import {
  SelectTroiPreferencesLoader,
  SelectTroiPreferencesWrapper,
} from "../pages/SelectTroiPreferences";
import Settings from "../pages/Settings";

const getSettingsRoutes = () => {
  const SettingsWithAlertNotifications = withAlertNotifications(Settings);
  const ResetTokenWithAlertNotifications = withAlertNotifications(ResetToken);
  const MusicServicesWithAlertNotifications = withAlertNotifications(
    MusicServices
  );
  const ImportWithAlertNotifications = withAlertNotifications(Import);
  const SelectTroiPreferencesWithAlertNotifications = withAlertNotifications(
    SelectTroiPreferencesWrapper
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
