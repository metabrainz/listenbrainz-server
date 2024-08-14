/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";

import { useLoaderData } from "react-router-dom";
import { Helmet } from "react-helmet";
import UserPins from "./components/UserPins";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getListenablePin } from "../../utils/utils";
import UserFeedback from "./components/UserFeedback";
import { useBrainzPlayerDispatch } from "../../common/brainzplayer/BrainzPlayerContext";

export type UserTasteProps = {
  feedback?: Array<FeedbackResponseWithTrackMetadata>;
  totalFeedbackCount: number;
  pins: PinnedRecording[];
  totalPinsCount: number;
  user: ListenBrainzUser;
};

type UserTasteLoaderData = UserTasteProps;

export default class UserTaste extends React.Component<UserTasteProps> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  render() {
    const {
      feedback,
      user,
      totalFeedbackCount,
      pins,
      totalPinsCount,
    } = this.props;
    const { currentUser } = this.context;
    return (
      <div role="main">
        <Helmet>
          <title>{`${
            user?.name === currentUser?.name ? "Your" : `${user?.name}'s`
          } Tastes`}</title>
        </Helmet>
        <div className="row">
          <div className="col-md-7">
            <UserFeedback
              feedback={feedback}
              totalCount={totalFeedbackCount}
              user={user}
            />
          </div>
          <div className="col-md-5">
            <UserPins user={user} pins={pins} totalCount={totalPinsCount} />
          </div>
        </div>
      </div>
    );
  }
}

export function UserTastesWrapper() {
  const data = useLoaderData() as UserTasteLoaderData;
  const { feedback, pins } = data;

  const RecordingMetadataToListenFormat = (
    feedbackItem: FeedbackResponseWithTrackMetadata
  ): Listen => {
    return {
      listened_at: feedbackItem.created ?? 0,
      track_metadata: { ...feedbackItem.track_metadata },
    };
  };

  const listensFromFeedback: BaseListenFormat[] =
    feedback
      // remove feedback items for which track metadata wasn't found. this usually means bad
      // msid or mbid data was submitted by the user.
      ?.filter((item) => item?.track_metadata)
      .map((feedbackItem) => RecordingMetadataToListenFormat(feedbackItem)) ??
    [];
  const listensFromPins = pins.map((pin) => {
    return getListenablePin(pin);
  });
  const listenables = [...listensFromFeedback, ...listensFromPins];

  const dispatch = useBrainzPlayerDispatch();

  React.useEffect(() => {
    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: listenables,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listenables]);

  return <UserTaste {...data} />;
}
