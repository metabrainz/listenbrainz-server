import * as React from "react";
import Card from "../../components/Card";
import GlobalAppContext from "../../utils/GlobalAppContext";

export type ListenCountCardProps = {
  listenCount?: number;
  user: ListenBrainzUser;
};

function ListenCountCard(props: ListenCountCardProps) {
  const { currentUser } = React.useContext(GlobalAppContext);
  const { listenCount, user } = props;
  const isCurrentUser = currentUser?.name === user?.name;

  let content;

  if (listenCount) {
    content = (
      <div data-testid="listen-count-card-content">
        {isCurrentUser ? "You have" : `${user.name} has`} listened to
        <hr />
        {listenCount.toLocaleString()}
        <br />
        <small className="text-muted">songs so far</small>
      </div>
    );
  } else {
    content = (
      <>
        <p className="text-muted">
          {isCurrentUser ? "Your" : `${user.name}'s`} listens count
        </p>
        <hr style={{ margin: "10px 0px" }} />
        <div style={{ fontSize: "14px" }} className="text-muted">
          {isCurrentUser ? "You haven't" : `${user.name} hasn't`} listened to
          any songs yet.
        </div>
      </>
    );
  }

  return (
    <Card id="listen-count-card" data-testid="listen-count-card">
      {content}
    </Card>
  );
}

export default ListenCountCard;
