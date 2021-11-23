import * as React from "react";
import { AlertList } from "react-bs-notifier";

export interface AlertNotificationsI {
  newAlert: (
    type: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
  onAlertDismissed: (alert: Alert) => void;
}

export interface AlertNotificationsProps {
  initialAlerts?: Array<Alert>;
}

export interface AlertNotificationsState {
  alerts: Array<Alert>;
}

export type WithAlertNotificationsInjectedProps = {
  newAlert: (
    type: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

export function withAlertNotifications<P extends object>(
  WrappedComponent: React.ComponentType<P & WithAlertNotificationsInjectedProps>
) {
  type CombinedProps = P & AlertNotificationsProps;
  class AlertNotifications
    extends React.Component<CombinedProps, AlertNotificationsState>
    implements AlertNotificationsI {
    constructor(props: CombinedProps) {
      super(props);
      this.state = {
        alerts: props.initialAlerts ?? [],
      };
    }

    newAlert = (
      type: AlertType,
      title: string,
      message: string | JSX.Element,
      count?: number
    ): void => {
      const newAlert: Alert = {
        id: new Date().getTime(),
        type,
        headline: title,
        message,
        count,
      };

      this.setState((prevState) => {
        const alertsList = prevState.alerts;
        for (let i = 0; i < alertsList.length; i += 1) {
          const item = alertsList[i];
          if (
            item.type === newAlert.type &&
            item.headline.startsWith(newAlert.headline) &&
            item.message === newAlert.message
          ) {
            if (!alertsList[i].count) {
              // If the count attribute is undefined, then Initializing it as 2
              alertsList[i].count = 2;
            } else {
              alertsList[i].count! += 1;
            }
            alertsList[i].headline = `${newAlert.headline} (${alertsList[i]
              .count!})`;
            return { alerts: alertsList };
          }
        }
        return {
          alerts: [...prevState.alerts, newAlert],
        };
      });
    };

    onAlertDismissed = (alert: Alert): void => {
      const { alerts } = this.state;

      // find the index of the alert that was dismissed
      const idx = alerts.indexOf(alert);

      if (idx >= 0) {
        this.setState({
          // remove the alert from the array
          alerts: [...alerts.slice(0, idx), ...alerts.slice(idx + 1)],
        });
      }
    };

    render() {
      const { alerts } = this.state;
      // Pass all props except initialAlerts to the wrapped component
      const { initialAlerts, ...passthroughProps } = this.props;
      return (
        <>
          <AlertList
            position="bottom-right"
            alerts={alerts}
            timeout={15000}
            dismissTitle="Dismiss"
            onDismiss={this.onAlertDismissed}
            showIcon={false}
          />
          <WrappedComponent
            {...(passthroughProps as P)}
            newAlert={this.newAlert}
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
