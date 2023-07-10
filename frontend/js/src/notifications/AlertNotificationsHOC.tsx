import * as React from "react";
import { ToastContainer } from "react-toastify";

export default function withAlertNotifications<P extends object>(
  WrappedComponent: React.ComponentType<P>
) {
  // eslint-disable-next-line react/prefer-stateless-function
  class AlertNotifications extends React.Component<P> {
    render() {
      return (
        <>
          <WrappedComponent {...(this.props as P)} />
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
        </>
      );
    }
  }

  (AlertNotifications as any).displayName = `WithAlertNotifications(${
    WrappedComponent.displayName || WrappedComponent.name || "Component"
  })`;
  return AlertNotifications;
}
