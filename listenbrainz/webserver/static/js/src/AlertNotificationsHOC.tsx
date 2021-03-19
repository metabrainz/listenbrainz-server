import * as React from "react";
import { AlertList } from "react-bs-notifier";
import RecentListens from "./RecentListens";

export interface AlertNotificationsProps {
  initialAlerts?: Array<Alert>;
  [name: string]: any;
}

export interface AlertNotificationsState {
  alerts: Array<Alert>;
}
function getDisplayName(WrappedComponent: React.ComponentType) {
  return WrappedComponent.displayName || WrappedComponent.name || "Component";
}

export function withAlertNotifications(
  WrappedComponent: React.ElementType
): React.ComponentType<AlertNotificationsProps> {
  class AlertNotifications extends React.Component<
    AlertNotificationsProps,
    AlertNotificationsState
  > {
    constructor(props: AlertNotificationsProps) {
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

    private onAlertDismissed = (alert: Alert): void => {
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
          />
          <WrappedComponent {...passthroughProps} newAlert={this.newAlert} />
        </>
      );
    }
  }

  (AlertNotifications as React.ComponentType).displayName = `WithAlertNotifications(${getDisplayName(
    WrappedComponent as React.ComponentType
  )})`;
  return AlertNotifications;
}
