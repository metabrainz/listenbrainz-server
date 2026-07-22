import * as React from "react";
import { Outlet, ScrollRestoration } from "react-router";
import { toast, ToastContainer, ToastOptions } from "react-toastify";
import localforage from "localforage";

import { Provider as NiceModalProvider } from "@ebay/nice-modal-react";
import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import ProtectedRoutes from "../utils/ProtectedRoutes";
import type { ServerAlert } from "../utils/utils";

const BrainzPlayer = React.lazy(() =>
  import("../common/brainzplayer/BrainzPlayer")
);

const mappingLevelToBootstrapClass = {
  default: "secondary",
  info: "info",
  success: "success",
  warning: "warning",
  error: "danger",
};

const dismissedInitialAlertsStore = localforage.createInstance({
  name: "listenbrainz",
  driver: [localforage.INDEXEDDB, localforage.LOCALSTORAGE],
  storeName: "dismissed-initial-alerts",
});

async function showInitialAlerts(initialAlerts: ServerAlert[]) {
  let dismissedInitialAlertIds = new Set<string>();
  try {
    dismissedInitialAlertIds = new Set(
      await dismissedInitialAlertsStore.keys()
    );
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(
      "Browser storage error, initial alert dismissals may not be remembered",
      error
    );
  }

  initialAlerts
    .filter((alert) => !dismissedInitialAlertIds.has(alert.id))
    .forEach((alert) => {
      const levelOrDefault = alert.level ?? "default";
      const bsClass = mappingLevelToBootstrapClass[levelOrDefault];
      const options: ToastOptions = {
        autoClose: false,
        closeOnClick: false,
        draggable: false,
        containerId: "initial-alerts",
        toastId: alert.id,
        type: levelOrDefault,
        className: `alert alert-${bsClass}`,
        onClose: () => {
          dismissedInitialAlertsStore.setItem(alert.id, true).catch((error) => {
            // eslint-disable-next-line no-console
            console.error(
              "LocalStorage error, initial alert dismissal may not be remembered",
              error
            );
          });
        },
      };
      const messageWithHTML = (
        // eslint-disable-next-line react/no-danger -- we control the content of the initial alerts, so this is safe
        <span dangerouslySetInnerHTML={{ __html: alert.message }} />
      );
      toast(messageWithHTML, options);
    });
}

export default function Layout({
  children,
  initialAlerts = [],
  withProtectedRoutes,
  withBrainzPlayer = true,
}: {
  children?: React.ReactNode;
  initialAlerts?: ServerAlert[];
  withProtectedRoutes?: boolean;
  withBrainzPlayer?: boolean;
}) {
  React.useEffect(() => {
    showInitialAlerts(initialAlerts);
  }, [initialAlerts]);

  return (
    <NiceModalProvider>
      <ToastContainer
        containerId="initial-alerts"
        position="top-center"
        autoClose={false}
        closeOnClick={false}
        hideProgressBar
        newestOnTop={false}
        rtl={false}
        theme="dark"
        style={{ width: "max(50%, 500px)", maxWidth: "100%" }}
        toastStyle={{ width: "100%" }}
        enableMultiContainer
        icon={false}
      />
      <ToastContainer
        position="bottom-right"
        autoClose={5000}
        hideProgressBar
        newestOnTop
        closeOnClick
        rtl={false}
        pauseOnHover
        theme="light"
        enableMultiContainer
      />
      <ScrollRestoration />
      <Navbar />
      <div className="container-react">
        <div className="container-react-main">
          {!withProtectedRoutes && <Outlet />}
          {children}
          {withProtectedRoutes && <ProtectedRoutes />}
          {withBrainzPlayer ? (
            <React.Suspense>
              <BrainzPlayer />
            </React.Suspense>
          ) : null}
        </div>
        <Footer />
      </div>
    </NiceModalProvider>
  );
}
