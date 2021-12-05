/* eslint-disable jsx-a11y/anchor-is-valid */

import * as ReactDOM from "react-dom";
import * as React from "react";
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
            <br />
            <br />
            <h1>{user?.name}</h1>
            <div style={{ marginTop: "20px", marginBottom: "20px" }}>
              <img
                src="{{ url_for('static', filename='img/musicbrainz-16.svg') }}"
                alt="MusicBrainz Logo"
              />
              <b>
                <a href={`https://musicbrainz.org/user/${user.name}`}>
                  See profile on MusicBrainz
                </a>
              </b>
            </div>

            <div className="card">
              <h4>
                Share your year with your friends
                <br />
                <br />
                <a
                  href={`https://listenbrainz.org/user/${user?.name}/year-in-music`}
                >
                  https://listenbrainz.org/user/{user?.name}/year-in-music
                </a>
              </h4>
            </div>
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
                      background: `rgb${fakeData.most_prominent_color}`,
                    }}
                  />
                </h3>
              </div>
            </div>
          </div>
          <hr className="wide" />
          <div className="row">
            <div className="card">
              <h3>
                Your top {selectedTopEntity}s of the year
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
              </h3>
              <ComponentToImage />
            </div>
          </div>
          <div className="row">
            <div className="col-sm-6 card">
              <h3 className="text-center">
                Your top discoveries published in 2021
              </h3>
              <div className="scrollable-area">
                Extract info from a JSPF playlist, show first 5 items, link to
                full playlist
              </div>
            </div>
            <div className="col-sm-6 card" id="new-releases">
              <h3 className="text-center">
                New albums of your top artists
                <div className="small">
                  New albums released in 2021 from your favorite artists.
                </div>
              </h3>
              <div className="scrollable-area">
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
          </div>
          <div className="row">
            <div className="col-sm-6 card" id="similar-users">
              <h3 className="text-center">
                Music buddies
                <div className="small">
                  Here are the users with the most similar taste to you this
                  year. Maybe go check them out?
                </div>
              </h3>
              <div className="scrollable-area similar-users-list">
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
            </div>
            <div className="col-sm-6 card" id="most-listened-year">
              <h3 className="text-center">
                What year are your favorite albums from?
                <div className="small">
                  It&apos;s one way of seeing how adventurous you&apos;ve been
                  this year, but we&apos;re not judging
                </div>
              </h3>
              <div className="graph">
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
          </div>
          <div className="row">
            <h3 className="text-center">
              We made some personnalized playlists for you !
            </h3>
          </div>
          <hr className="wide" />
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
