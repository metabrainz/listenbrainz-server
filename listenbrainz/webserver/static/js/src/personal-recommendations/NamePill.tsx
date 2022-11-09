import * as React from "react";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import { isFunction } from "lodash";
import ListenControl from "../listens/ListenControl";

export type NamePillProps = {
  title: string;
  closeAction?: (event: React.MouseEvent) => void;
};

function NamePill(props: NamePillProps) {
  const { title, closeAction } = props;
  return (
    <div className="pill">
      <div>
        <span>{title}</span>
        {isFunction(closeAction) && (
          <ListenControl text="" icon={faTimesCircle} action={closeAction} />
        )}
      </div>
    </div>
  );
}

export default NamePill;
