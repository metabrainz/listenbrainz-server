import * as React from "react";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import ListenControl from "../listens/ListenControl";

export type PillProps = {
  title: string;
  closeAction?: (event: React.MouseEvent) => void;
  closeButton?: Boolean;
};

const Pill = (props: PillProps) => {
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

export default Pill;
