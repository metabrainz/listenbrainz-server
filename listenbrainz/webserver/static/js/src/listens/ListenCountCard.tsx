import * as React from "react";
import Card from "../components/Card";
import GlobalAppContext from "../utils/GlobalAppContext";

export type ListenCountCardProps = {
  listenCount?: number;
  user: ListenBrainzUser;
};

const ListenCountCard = (props: ListenCountCardProps) => {
  const { currentUser } = React.useContext(GlobalAppContext);
  const { listenCount, user } = props;
  const isCurrentUser = currentUser?.name === user?.name;

  return (
    <Card id="listen-count-card">
      {listenCount && (
        <div>
          {isCurrentUser
            ? "You have listened to"
            : `${user.name} has listened to`}
          <hr />
          {listenCount.toLocaleString()}
          <br />
          <small className="text-muted">songs so far</small>
        </div>
      )}
      {!listenCount && (
        <p>
          {isCurrentUser
            ? "You have not listened to any songs so far"
            : `${user.name} has not listened to any songs so far`}
        </p>
      )}
    </Card>
  );
};

export default ListenCountCard;
