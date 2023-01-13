import * as React from "react";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import { isFunction } from "lodash";
import ListenControl from "../listens/ListenControl";

export type PillProps = {
  title: string;
  closeAction?: (event: React.MouseEvent) => void;
};

export type PillState = {};

export default class Pill extends React.Component<PillProps, PillState> {
  render() {
    const { title, closeAction } = this.props;
    return (
      <div className="playlistPill">
        <div>
          <span>{title}</span>
          {isFunction(closeAction) && (
            <ListenControl text="" icon={faTimesCircle} action={closeAction} />
          )}
        </div>
      </div>
    );
  }
}
