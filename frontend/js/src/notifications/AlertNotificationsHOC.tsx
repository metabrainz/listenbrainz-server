import * as React from "react";
import { ToastContainer } from "react-toastify";

export function withAlertNotifications<P extends object>(
  WrappedComponent: React.ComponentType<P>
) {
  class AlertNotifications extends React.Component<P> {
    render() {
      // Pass all props except initialAlerts to the wrapped component
      const { ...passthroughProps } = this.props;
      return (
        <>
          <WrappedComponent {...(passthroughProps as P)} />
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
