/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import { useLoaderData } from "react-router-dom";
import { Helmet } from "react-helmet";

import ListenCard from "../common/listens/ListenCard";
import Card from "../components/Card";

import { getTrackName } from "../utils/utils";
import { useBrainzPlayerDispatch } from "../common/brainzplayer/BrainzPlayerContext";
import RecentDonorsCard from "./components/RecentDonors";
import FlairsExplanationButton from "../common/flairs/FlairsExplanationButton";

export type RecentListensProps = {
  listens: Array<Listen>;
  globalListenCount: number;
  globalUserCount: string;
  recentDonors: Array<DonationInfoWithPinnedRecording>;
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
  constructor(props: RecentListensProps) {
    super(props);
    this.state = {
      listens: props.listens || [],
    };
  }

  render() {
    const { listens } = this.state;
    const { globalListenCount, globalUserCount, recentDonors } = this.props;

    return (
      <div role="main">
        <Helmet>
          <title>Recent listens</title>
        </Helmet>
        <div className="listen-header">
          <h3 className="header-with-line">Global listens</h3>
        </div>
        <div className="row">
          <div className="col-md-4 col-md-push-8">
            <Card id="listen-count-card">
              <div>
                {globalListenCount?.toLocaleString() ?? "-"}
                <br />
                <small className="text-muted">songs played</small>
              </div>
            </Card>
            <Card id="listen-count-card" className="card-user-sn">
              <div>
                {globalUserCount ?? "-"}
                <br />
                <small className="text-muted">users</small>
              </div>
            </Card>
            <Card className="hidden-xs">
              <RecentDonorsCard donors={recentDonors} />
            </Card>
            <FlairsExplanationButton className="hidden-xs" />
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
      </div>
    );
  }
}

export function RecentListensWrapper() {
  const data = useLoaderData() as RecentListensLoaderData;
  const listens = data.listens || [];
  const dispatch = useBrainzPlayerDispatch();

  React.useEffect(() => {
    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: listens,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listens]);
  return <RecentListens {...data} />;
}
