import * as React from "react";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import { isFunction } from "lodash";
import ListenControl from "../listens/ListenControl";

export type PillProps = {
  collaboratorName: string;
  removeCollaborator?: (event: React.MouseEvent) => void;
};

export type PillState = {};

export default class Pill extends React.Component<PillProps, PillState> {
  render() {
    const { collaboratorName, removeCollaborator } = this.props;
    return (
      <div className="playlistPill">
        <div>
          <span>{collaboratorName}</span>
          {isFunction(removeCollaborator) && (
            <ListenControl text="" icon={faTimesCircle} action={removeCollaborator} />
          )}
        </div>
      </div>
    );
  }
}
