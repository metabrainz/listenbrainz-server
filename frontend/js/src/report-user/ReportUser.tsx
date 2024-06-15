/*
 * listenbrainz-server - Server for the ListenBrainz project.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

import * as React from "react";
import { toast } from "react-toastify";
import GlobalAppContext from "../utils/GlobalAppContext";
import ReportUserModal from "./ReportUserModal";

type ReportUserButtonProps = {
  user: ListenBrainzUser;
  alreadyReported: boolean;
};

type ReportUserButtonState = {
  reported: boolean;
  error: boolean;
};

class ReportUserButton extends React.Component<
  ReportUserButtonProps,
  ReportUserButtonState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  constructor(props: ReportUserButtonProps) {
    super(props);
    const reported = props.alreadyReported;
    this.state = { reported, error: false };
  }

  handleSubmit = (optionalReason?: string) => {
    const { APIService } = this.context;
    const { user } = this.props;
    APIService.reportUser(user.name, optionalReason)
      .then(() => {
        this.setState({
          reported: true,
        });
      })
      .catch((error: Error) => {
        toast.error(error.message);
        this.setState({
          error: true,
        });
      });
  };

  render() {
    const { reported, error } = this.state;
    const { user } = this.props;
    let buttonText: string;
    if (error) {
      buttonText = "Error! Try Again";
    } else if (reported) {
      buttonText = "Report Submitted";
    } else {
      buttonText = "Report User";
    }
    return (
      <>
        <button
          className="btn btn-danger"
          style={{ float: "right" }}
          data-toggle="modal"
          data-target="#reportUserModal"
          type="button"
        >
          {buttonText}
        </button>
        <ReportUserModal
          onSubmit={this.handleSubmit}
          reportedUserName={user.name}
        />
      </>
    );
  }
}

export default ReportUserButton;
