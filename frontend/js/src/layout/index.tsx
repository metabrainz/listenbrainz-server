import * as React from "react";
import { Outlet, ScrollRestoration } from "react-router-dom";
import { ToastContainer } from "react-toastify";

import { Provider as NiceModalProvider } from "@ebay/nice-modal-react";
import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import ProtectedRoutes from "../utils/ProtectedRoutes";

const BrainzPlayer = React.lazy(() =>
  import("../common/brainzplayer/BrainzPlayer")
);

export default function Layout({
  children,
  withProtectedRoutes,
  withBrainzPlayer = true,
}: {
  children?: React.ReactNode;
  withProtectedRoutes?: boolean;
  withBrainzPlayer?: boolean;
}) {
  return (
    <NiceModalProvider>
      <ToastContainer
        position="bottom-right"
        autoClose={5000}
        hideProgressBar
        newestOnTop
        closeOnClick
        rtl={false}
        pauseOnHover
        theme="light"
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
