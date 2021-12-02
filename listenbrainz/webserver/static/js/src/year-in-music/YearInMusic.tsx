/* eslint-disable jsx-a11y/anchor-is-valid */

import * as ReactDOM from "react-dom";
import * as React from "react";
import { paddingTop } from "html2canvas/dist/types/css/property-descriptors/padding";
import { ResponsiveBar } from "@nivo/bar";
import ErrorBoundary from "../ErrorBoundary";
import GlobalAppContext, { GlobalAppContextT } from "../GlobalAppContext";
import BrainzPlayer from "../BrainzPlayer";
import Pill from "../components/Pill";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../AlertNotificationsHOC";

import APIServiceClass from "../APIService";
import { getPageProps } from "../utils";
import ComponentToImage from "./ComponentToImage";

import fakeData from "./year-in-music-data.json";
import ListenCard from "../listens/ListenCard";
import UserListModalEntry from "../follow/UserListModalEntry";

export type YearInMusicProps = {
  user: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export type YearInMusicState = {
  loading: boolean;
  selectedRelease?: ColorReleaseItem;
  selectedTopEntity: Entity;
};

export default class YearInMusic extends React.Component<
  YearInMusicProps,
  YearInMusicState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: YearInMusicProps) {
    super(props);
    this.state = {
      loading: false,
      selectedTopEntity: "recording",
    };
  }

  selectTopEntity = (entity: Entity) => {
    this.setState({ selectedTopEntity: entity });
  };

  render() {
    const { user, newAlert } = this.props;
    const { loading, selectedRelease, selectedTopEntity } = this.state;
    const { APIService, currentUser } = this.context;
    const selectedReleaseTracks = selectedRelease?.recordings ?? [];
    const totalListens = 12345;
    const mostActiveDay = "Friday";
    return (
      <div role="main" id="year-in-music">
        <div className="row center-block">
          <div className="col-sm-6">
            <div className="card">
              {user?.name}
              <h4>Share your year with your friends</h4>
              <a
                href={`https://listenbrainz.org/user/${user?.name}/year-in-music`}
              >
                https://listenbrainz.org/user/{user?.name}/year-in-music
              </a>
            </div>
            <strong>listened to {totalListens} tracks</strong>
            <strong>mostly on {fakeData.day_of_week}</strong>
          </div>
          <div className="col-sm-6">
            <img
              className="img-responsive header-image"
              src="/static/img/year-in-music-2021.svg"
              alt="Your year in music 2021"
            />
          </div>
          <hr className="wide" />
          <div className="row">
            <div className="col-sm-4">
              <div className="card flex-center">
                <h3 className="text-center">
                  You listened to 12345 songs this year
                </h3>
              </div>
            </div>
            <div className="col-sm-4">
              <div className="card flex-center">
                <h3 className="text-center">Your most active listening day</h3>
                <div>Friday</div>
              </div>
            </div>
            <div className="col-sm-4">
              <div className="card flex-center">
                <h3 className="text-center">
                  Average color of your top albums:
                  <div
                    style={{
                      width: "100%",
                      height: "65px",
                      color: `rgb${fakeData.most_prominent_color}`,
                    }}
                  />
                </h3>
              </div>
            </div>
          </div>
          <hr className="wide" />
          <div className="row">
            <div className="card flex-center">
              <h3 className="text-center">
                Your top{" "}
                <Pill
                  active={selectedTopEntity === "recording"}
                  // eslint-disable-next-line react/jsx-no-bind
                  onClick={this.selectTopEntity.bind(this, "recording")}
                >
                  Tracks
                </Pill>{" "}
                <Pill
                  active={selectedTopEntity === "release"}
                  // eslint-disable-next-line react/jsx-no-bind
                  onClick={this.selectTopEntity.bind(this, "release")}
                >
                  Albums
                </Pill>{" "}
                <Pill
                  active={selectedTopEntity === "artist"}
                  // eslint-disable-next-line react/jsx-no-bind
                  onClick={this.selectTopEntity.bind(this, "artist")}
                >
                  Artists
                </Pill>{" "}
                of the year
              </h3>
              <div>{selectedTopEntity}</div>
            </div>
          </div>
          <div className="row">
            <div className="col-sm-6 card">
              <h3 className="text-center">
                Your top discoveries published in 2021
              </h3>
            </div>
            <div className="col-sm-6 card" id="new-releases">
              <h3 className="text-center">New albums of your top artists</h3>
              <span>
                New albums released in 2021 from your favorite artists.
              </span>
              {fakeData.new_releases_of_top_artists.map((release) => (
                <ListenCard
                  key={release.release_id}
                  compact
                  listen={{
                    listened_at: 0,
                    listened_at_iso: release.first_release_date,
                    track_metadata: {
                      artist_name: release.artist_credit_names.join(", "),
                      track_name: release.title,
                      release_name: release.title,
                      additional_info: {
                        release_mbid: release.release_id,
                        artist_mbids: release.artist_credit_mbids,
                      },
                    },
                  }}
                  showTimestamp
                  showUsername={false}
                  newAlert={newAlert}
                />
              ))}
            </div>
          </div>
          <div className="row">
            <div className="col-sm-6 card" id="similar-users">
              <h3 className="text-center">Music buddies</h3>
              <span>
                Here are the users with the most similar taste to you this year.
                Maybe go check them out?
              </span>
              {fakeData.similar_users &&
                Object.keys(fakeData.similar_users).map(
                  (userName: string, index) => {
                    return (
                      <UserListModalEntry
                        mode="similar-users"
                        key={userName}
                        user={{
                          name: userName,
                          similarityScore:
                            fakeData.similar_users[
                              userName as keyof typeof fakeData.similar_users
                            ],
                        }}
                        loggedInUserFollowsUser={false}
                        updateFollowingList={() => {}}
                      />
                    );
                  }
                )}
            </div>
            <div className="col-sm-6 card" id="most-listened-year">
              <h3 className="text-center">How old is your favorite music?</h3>
              <div>
                It&apos;s one way of seeing how adventurous you&apos;ve been
                this year, but we&apos;re not judging
              </div>
              <ResponsiveBar
                margin={{ left: 30, bottom: 130 }}
                data={Object.keys(fakeData.most_listened_year).map(
                  (year: string, index) => ({
                    year: Number(year),
                    albums:
                      fakeData.most_listened_year[
                        year as keyof typeof fakeData.most_listened_year
                      ],
                  })
                )}
                padding={0.2}
                layout="horizontal"
                keys={["albums"]}
                indexBy="year"
              />
            </div>
          </div>
          <div className="row">
            <h3 className="text-center">
              We made some personnalized playlists for you !
            </h3>
          </div>
          <hr className="wide" />
          <ComponentToImage />
          <BrainzPlayer
            listens={[]}
            newAlert={newAlert}
            listenBrainzAPIBaseURI={APIService.APIBaseURI}
            refreshSpotifyToken={APIService.refreshSpotifyToken}
            refreshYoutubeToken={APIService.refreshYoutubeToken}
          />
        </div>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalReactProps } = getPageProps();
  const { api_url, current_user, spotify, youtube } = globalReactProps;
  const { user } = reactProps;

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const YearInMusicWithAlertNotifications = withAlertNotifications(YearInMusic);

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <YearInMusicWithAlertNotifications user={user} />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
