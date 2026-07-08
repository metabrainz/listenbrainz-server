import * as React from "react";
import { Outlet, ScrollRestoration } from "react-router";
import { toast, ToastContainer, ToastOptions } from "react-toastify";

import { Provider as NiceModalProvider } from "@ebay/nice-modal-react";
import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import ProtectedRoutes from "../utils/ProtectedRoutes";
import type { ServerAlert } from "../utils/utils";

const BrainzPlayer = React.lazy(() =>
  import("../common/brainzplayer/BrainzPlayer")
);

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
    initialAlerts.forEach((alert) => {
      const levelOrDefault = alert.level ?? "default";
      const options: ToastOptions = {
        autoClose: false,
        closeOnClick: false,
        containerId: "initial-alerts",
        toastId: alert.id,
        type: levelOrDefault,
        className: `alert alert-${levelOrDefault}`,
      };
      const messageWithHTML = (
        // eslint-disable-next-line react/no-danger -- we control the content of the initial alerts, so this is safe
        <span dangerouslySetInnerHTML={{ __html: alert.message }} />
      );
      toast(messageWithHTML, options);
    });
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
