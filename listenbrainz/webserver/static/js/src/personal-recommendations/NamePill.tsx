import * as React from "react";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import { isFunction } from "lodash";
import ListenControl from "../listens/ListenControl";

export type NamePillProps = {
  title: string;
  closeAction?: (event: React.MouseEvent) => void;
  closeButton?: Boolean;
};

const NamePill = (props: NamePillProps) => {
  const { title, closeAction, closeButton } = props;
  return (
    <div className="pill">
      <div>
        <span>{title}</span>
        {closeButton && (
          <ListenControl text="" icon={faTimesCircle} action={closeAction} />
        )}
      </div>
    </div>
  );
};

export default NamePill;
