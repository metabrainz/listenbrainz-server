import * as React from "react";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import ListenControl from "../listens/ListenControl";

export type PillProps = {
  title: string;
  closeAction?: (event: React.MouseEvent) => void;
};

const Pill = (props: PillProps) => {
  const { title, closeAction } = props;
  return (
    <div className="pill">
      <div>
        <p>{title}</p>
        <ListenControl text="" icon={faTimesCircle} action={closeAction} />
      </div>
    </div>
  );
};

export default Pill;
