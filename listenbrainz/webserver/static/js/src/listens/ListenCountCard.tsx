import * as React from "react";
import Card from "../components/Card";

export type ListenCountCardProps = {
  listenCount?: number;
};

const ListenCountCard = (props: ListenCountCardProps) => {
  const { listenCount } = props;

  return (
    <Card id="listen-count-card" style={{ fontSize: 24 }}>
      {listenCount && (
        <p>
          You have listened to
          <hr style={{ marginTop: 12, marginBottom: 12 }} />
          {listenCount.toLocaleString()}
          <br />
          <small className="text-muted">songs so far</small>
        </p>
      )}
      {!listenCount && <p>You have not listened to any songs so far</p>}
    </Card>
  );
};

export default ListenCountCard;
