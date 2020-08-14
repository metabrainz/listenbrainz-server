import * as React from "react";
import Card from "../components/Card";

export type ListenCountCardProps = {
  listenCount?: number;
};

const ListenCountCard = (props: ListenCountCardProps) => {
  const { listenCount } = props;

  return (
    <Card id="listen-count-card">
      <h4>
        You have listened to
        <hr />
      </h4>
      <div>
        <h4>{listenCount}</h4>
        <small className="text-muted">songs so far</small>
      </div>
    </Card>
  );
};

export default ListenCountCard;
