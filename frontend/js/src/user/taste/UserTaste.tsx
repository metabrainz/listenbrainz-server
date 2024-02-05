/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";

import { useLoaderData } from "react-router-dom";
import { Helmet } from "react-helmet";
import BrainzPlayer from "../../common/brainzplayer/BrainzPlayer";
import UserPins from "./components/UserPins";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getListenablePin } from "../../utils/utils";
import UserFeedback from "./components/UserFeedback";

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
  static RecordingMetadataToListenFormat = (
    feedbackItem: FeedbackResponseWithTrackMetadata
  ): Listen => {
    return {
      listened_at: feedbackItem.created ?? 0,
      track_metadata: { ...feedbackItem.track_metadata },
    };
  };

  declare context: React.ContextType<typeof GlobalAppContext>;

  render() {
    const {
      feedback,
      user,
      totalFeedbackCount,
      pins,
      totalPinsCount,
    } = this.props;
    const { APIService, currentUser } = this.context;
    const listensFromFeedback: BaseListenFormat[] =
      feedback
        // remove feedback items for which track metadata wasn't found. this usually means bad
        // msid or mbid data was submitted by the user.
        ?.filter((item) => item?.track_metadata)
        .map((feedbackItem) =>
          UserTaste.RecordingMetadataToListenFormat(feedbackItem)
        ) ?? [];
    const listensFromPins = pins.map((pin) => {
      return getListenablePin(pin);
    });
    const listenables = [...listensFromFeedback, ...listensFromPins];
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
        <BrainzPlayer
          listens={listenables}
          listenBrainzAPIBaseURI={APIService.APIBaseURI}
          refreshSpotifyToken={APIService.refreshSpotifyToken}
          refreshYoutubeToken={APIService.refreshYoutubeToken}
          refreshSoundcloudToken={APIService.refreshSoundcloudToken}
        />
      </div>
    );
  }
}

export function UserTastesWrapper() {
  const data = useLoaderData() as UserTasteLoaderData;
  return <UserTaste {...data} />;
}

export const UserTasteLoader = async ({ request }: { request: Request }) => {
  const response = await fetch(request.url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });
  const data = await response.json();
  return { ...data };
};
