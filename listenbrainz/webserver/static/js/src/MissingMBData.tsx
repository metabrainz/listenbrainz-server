import * as React from "react";
import * as ReactDOM from "react-dom";
import * as Sentry from "@sentry/react";

import { get, isEqual } from "lodash";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../AlertNotificationsHOC";

import APIServiceClass from "../APIService";
import GlobalAppContext, { GlobalAppContextT } from "../GlobalAppContext";
import ErrorBoundary from "../ErrorBoundary";
import Loader from "../components/Loader";
import { getPageProps } from "../utils";
import ListenCard from "../listens/ListenCard";

export type MissingMBDataProps = {
  missingData?: Array<MissingMBData>;
  user: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export interface MissingMBDataState = {
  missingData?: Array<MissingMBData>;
  currPage?: number;
  totalPages?: number;
}

export default class MissingMBDataPage extends React.Component<
  MissingMBDataProps,
  MissingMBDataState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  private expectedDataPerPage = 25;
  private APIService!: APIServiceClass; //don't know if needed or not

  constructor(props: MissingMBDataProps) {
    super(props);
    this.state = {
      missingData: props.missingData?.slice(0, this.expectedDataPerPage) || [],
      currPage: 1,
      totalPages: props.missingData ? Math.ceil(props.missingData.length / this.expectedDataPerPage) : 0,
    }
  }

  render(){
    const {
      missingData,
      currPage,
      totalPages,
    } = this.state;
    const {user, newAlert} = this.props;
    const {currentUser} = this.context;
    const isCurrentUser =
      Boolean(currentUser?.name) && currentUser?.name === user?.name;
    return(
      <div role="main">
        <div className="row">
          <div className="col-md-8">
            <div>
              <div
                style={{
                  height: "0",
                  position: "sticky",
                  top: "50%",
                  zIndex: 1,
                }}
              >
              </div>
              <div
                id="missingMBData"
              >

    )
  }
}
