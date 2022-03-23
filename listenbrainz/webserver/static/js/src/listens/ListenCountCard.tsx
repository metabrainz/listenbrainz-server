import * as React from "react";
import Card from "../components/Card";

export type ListenCountCardProps = {
  listenCount?: number;
};

const ListenCountCard = (props: ListenCountCardProps) => {
  const { listenCount } = props;

  return (
    <Card id="listen-count-card">
      {listenCount && (
        <div>
          You have listened to
          <hr />
          {listenCount.toLocaleString()}
          <br />
          <small className="text-muted">songs so far</small>
        </div>
      )}
      {!listenCount && <p>You have not listened to any songs so far</p>}
    </Card>
  );
};

export default ListenCountCard;
