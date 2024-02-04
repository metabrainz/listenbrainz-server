/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import { useLoaderData } from "react-router-dom";
import { Helmet } from "react-helmet";
import GlobalAppContext from "../utils/GlobalAppContext";

import BrainzPlayer from "../common/brainzplayer/BrainzPlayer";
import ListenCard from "../common/listens/ListenCard";
import Card from "../components/Card";

import { getTrackName } from "../utils/utils";

export type RecentListensProps = {
  listens: Array<Listen>;
  globalListenCount: number;
  globalUserCount: string;
};

type RecentListensLoaderData = RecentListensProps;

export interface RecentListensState {
  listens: Array<Listen>;
  listenCount?: number;
}

export default class RecentListens extends React.Component<
  RecentListensProps,
  RecentListensState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: RecentListensProps) {
    super(props);
    this.state = {
      listens: props.listens || [],
    };
  }

  render() {
    const { listens } = this.state;
    const { globalListenCount, globalUserCount } = this.props;
    const { APIService, currentUser } = this.context;

    return (
      <div role="main">
        <Helmet>
          <title>Recent listens - ListenBrainz</title>
        </Helmet>
        <h3>Global listens</h3>
        <div className="row">
          <div className="col-md-4 col-md-push-8">
            <Card id="listen-count-card">
              <div>
                {globalListenCount?.toLocaleString() ?? "-"}
                <br />
                <small className="text-muted">songs played</small>
              </div>
            </Card>
            <Card id="listen-count-card">
              <div>
                {globalUserCount ?? "-"}
                <br />
                <small className="text-muted">users</small>
              </div>
            </Card>
          </div>
          <div className="col-md-8 col-md-pull-4">
            {!listens.length && (
              <h5 className="text-center">No listens to show</h5>
            )}
            {listens.length > 0 && (
              <div id="listens">
                {listens.map((listen) => {
                  return (
                    <ListenCard
                      key={`${listen.listened_at}-${getTrackName(listen)}-${
                        listen.user_name
                      }`}
                      showTimestamp
                      showUsername
                      listen={listen}
                    />
                  );
                })}
              </div>
            )}
          </div>
        </div>
        <BrainzPlayer
          listens={listens}
          listenBrainzAPIBaseURI={APIService.APIBaseURI}
          refreshSpotifyToken={APIService.refreshSpotifyToken}
          refreshYoutubeToken={APIService.refreshYoutubeToken}
          refreshSoundcloudToken={APIService.refreshSoundcloudToken}
        />
      </div>
    );
  }
}

export function RecentListensWrapper() {
  const data = useLoaderData() as RecentListensLoaderData;
  return <RecentListens {...data} />;
}

export const RecentListensLoader = async ({
  request,
}: {
  request: Request;
}) => {
  const response = await fetch(request.url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });
  const data = await response.json();
  return { ...data };
};
