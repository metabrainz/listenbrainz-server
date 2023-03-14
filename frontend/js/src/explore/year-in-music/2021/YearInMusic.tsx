import { createRoot } from "react-dom/client";
import * as React from "react";
import { ResponsiveBar } from "@nivo/bar";
import { Navigation, Keyboard, EffectCoverflow } from "swiper";
import { Swiper, SwiperSlide } from "swiper/react";
import { CalendarDatum, ResponsiveCalendar } from "@nivo/calendar";
import {
  get,
  has,
  isEmpty,
  isNil,
  isString,
  range,
  uniq,
  capitalize,
  toPairs,
} from "lodash";
import NiceModal from "@ebay/nice-modal-react";
import ErrorBoundary from "../../../utils/ErrorBoundary";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../utils/GlobalAppContext";
import BrainzPlayer from "../../../brainzplayer/BrainzPlayer";

import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../../../notifications/AlertNotificationsHOC";

import { getPageProps } from "../../../utils/utils";
import { getEntityLink } from "../../../stats/utils";
import ComponentToImage from "./ComponentToImage";

import ListenCard from "../../../listens/ListenCard";
import UserListModalEntry from "../../../follow/UserListModalEntry";
import {
  JSPFTrackToListen,
  MUSICBRAINZ_JSPF_TRACK_EXTENSION,
} from "../../../playlists/utils";
import FollowButton from "../../../follow/FollowButton";
import { COLOR_LB_ORANGE } from "../../../utils/constants";

export type YearInMusicProps = {
  user: ListenBrainzUser;
  yearInMusicData: {
    day_of_week: string;
    top_artists: Array<{
      artist_name: string;
      artist_mbids: string[];
      listen_count: number;
    }>;
    top_releases: Array<{
      artist_name: string;
      artist_mbids: string[];
      listen_count: number;
      release_name: string;
      release_mbid: string;
      cover_art_src?: string;
    }>;
    top_releases_coverart: { [key: string]: string };
    top_recordings: Array<{
      artist_name: string;
      artist_mbids: string[];
      listen_count: number;
      release_name: string;
      release_mbid: string;
      track_name: string;
      recording_mbid: string;
    }>;
    similar_users: { [key: string]: number };
    listens_per_day: Array<{
      to_ts: number;
      from_ts: number;
      time_range: string;
      listen_count: number;
    }>;
    most_listened_year: { [key: string]: number };
    total_listen_count: number;
    most_prominent_color: string;
    new_releases_of_top_artists: Array<{
      type: string;
      title: string;
      release_mbid: string;
      first_release_date: string;
      artist_credit_mbids: string[];
      artist_credit_names: string[];
    }>;
  };
} & WithAlertNotificationsInjectedProps;

export type YearInMusicState = {
  followingList: Array<string>;
  activeCoverflowImage: number;
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
      followingList: [],
      activeCoverflowImage: 0,
    };
  }

  async componentDidMount() {
    await this.getFollowing();
    // Some issue with the coverflow library
    setTimeout(() => {
      this.setState({ activeCoverflowImage: 3 });
    }, 500);
  }

  private getPlaylistByName(
    playlistName: string,
    description?: string
  ): { jspf: JSPFObject; mbid: string; description?: string } | undefined {
    const uuidMatch = /[0-9a-f]{8}\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\b[0-9a-f]{12}/g;
    /* We generated some playlists with this incorrect value as the track extension key, rewrite it if it exists */
    const badPlaylistTrackExtensionValue = "https://musicbrainz.org/recording/";
    const { yearInMusicData } = this.props;
    let playlist;
    try {
      const rawPlaylist = get(yearInMusicData, playlistName);
      const coverArt = get(yearInMusicData, `${playlistName}-coverart`);
      playlist = isString(rawPlaylist) ? JSON.parse(rawPlaylist) : rawPlaylist;
      // Append manual description used in this page (rather than parsing HTML, ellipsis issues, etc.)
      if (description) {
        playlist.description = description;
      }
      /* Add a track image if it exists in the `{playlistName}-coverart` key */
      playlist.jspf.playlist.track = playlist.jspf.playlist.track.map(
        (track: JSPFTrack) => {
          const newTrack = { ...track };
          const track_id = track.identifier;
          const found = track_id.match(uuidMatch);
          if (found) {
            const recording_mbid = found[0];
            newTrack.id = recording_mbid;
            const recording_coverart = coverArt?.[recording_mbid];
            if (recording_coverart) {
              newTrack.image = recording_coverart;
            }
          }
          if (
            newTrack.extension &&
            track.extension?.[badPlaylistTrackExtensionValue]
          ) {
            newTrack.extension[MUSICBRAINZ_JSPF_TRACK_EXTENSION] =
              track.extension[badPlaylistTrackExtensionValue];
          }
          const trackExtension =
            newTrack?.extension?.[MUSICBRAINZ_JSPF_TRACK_EXTENSION];
          // See https://github.com/metabrainz/listenbrainz-server/pull/1839 for context
          if (trackExtension && has(trackExtension, "artist_mbids")) {
            //  Using some forbiddden (but oh so sweet) ts-ignore as we're fixing objects that don't fit the expected type
            // @ts-ignore
            trackExtension.artist_identifiers = trackExtension.artist_mbids;
            // @ts-ignore
            delete trackExtension.artist_mbids;
          }
          return newTrack;
        }
      );
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error(`"Error parsing ${playlistName}:`, error);
    }
    return playlist;
  }

  getFollowing = async () => {
    const { APIService, currentUser } = this.context;
    const { getFollowingForUser } = APIService;
    if (!currentUser?.name) {
      return;
    }
    try {
      const response = await getFollowingForUser(currentUser.name);
      const { following } = response;

      this.setState({ followingList: following });
    } catch (err) {
      const { newAlert } = this.props;
      newAlert("danger", "Error while fetching followers", err.toString());
    }
  };

  updateFollowingList = (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => {
    const { followingList } = this.state;
    const newFollowingList = [...followingList];
    const index = newFollowingList.findIndex(
      (following) => following === user.name
    );
    if (action === "follow" && index === -1) {
      newFollowingList.push(user.name);
    }
    if (action === "unfollow" && index !== -1) {
      newFollowingList.splice(index, 1);
    }
    this.setState({ followingList: newFollowingList });
  };

  loggedInUserFollowsUser = (user: ListenBrainzUser): boolean => {
    const { currentUser } = this.context;
    const { followingList } = this.state;

    if (isNil(currentUser) || isEmpty(currentUser)) {
      return false;
    }

    return followingList.includes(user.name);
  };

  render() {
    const { user, newAlert, yearInMusicData } = this.props;
    const { APIService, currentUser } = this.context;
    const { activeCoverflowImage } = this.state;
    const listens: BaseListenFormat[] = [];

    if (!yearInMusicData || isEmpty(yearInMusicData)) {
      return (
        <div className="flex-center flex-wrap">
          <h3>
            We don&apos;t have enough listening data for {user.name} to produce
            any statistics or playlists. (If you received an email from us
            telling you that you had a report waiting for you, we apologize for
            the goof-up. We don&apos;t -- 2022 continues to suck, sorry!)
          </h3>
          <p>
            Check out how you can submit listens by{" "}
            <a href="/profile/music-services/details/">
              connecting a music service
            </a>{" "}
            or <a href="/profile/import/">importing your listening history</a>,
            and come back next year!
          </p>
        </div>
      );
    }
    // Some data might not have been calculated for some users
    // This boolean lets us warn them of that
    let missingSomeData = false;

    if (
      !yearInMusicData.top_releases ||
      !yearInMusicData.top_recordings ||
      !yearInMusicData.top_artists ||
      !yearInMusicData.listens_per_day ||
      !yearInMusicData.total_listen_count ||
      !yearInMusicData.day_of_week ||
      !yearInMusicData.new_releases_of_top_artists
    ) {
      missingSomeData = true;
    }

    // Is the logged-in user looking at their own page?
    const isCurrentUser = user.name === currentUser?.name;
    const youOrUsername = isCurrentUser ? "you" : `${user.name}`;
    const yourOrUsersName = isCurrentUser ? "your" : `${user.name}'s`;

    /* Most listened years */
    let mostListenedYearDataForGraph;
    if (isEmpty(yearInMusicData.most_listened_year)) {
      missingSomeData = true;
    } else {
      const mostListenedYears = Object.keys(yearInMusicData.most_listened_year);
      // Ensure there are no holes between years
      const filledYears = range(
        Number(mostListenedYears[0]),
        Number(mostListenedYears[mostListenedYears.length - 1])
      );
      mostListenedYearDataForGraph = filledYears.map((year: number) => ({
        year,
        // Set to 0 for years without data
        songs: String(yearInMusicData.most_listened_year[String(year)] ?? 0),
      }));
    }

    /* Similar users sorted by similarity score */
    let sortedSimilarUsers;
    if (isEmpty(yearInMusicData.similar_users)) {
      missingSomeData = true;
    } else {
      sortedSimilarUsers = toPairs(yearInMusicData.similar_users).sort(
        (a, b) => b[1] - a[1]
      );
    }

    /* Listening history calendar graph */
    let listensPerDayForGraph;
    if (isEmpty(yearInMusicData.listens_per_day)) {
      missingSomeData = true;
    } else {
      listensPerDayForGraph = yearInMusicData.listens_per_day
        .map((datum) =>
          datum.listen_count > 0
            ? {
                day: new Date(datum.time_range).toLocaleDateString("en-CA"),
                value: datum.listen_count,
              }
            : // Return null if the value is 0
              null
        )
        // Filter out null entries in the array
        .filter(Boolean);
    }

    /* Playlists */
    const topDiscoveriesPlaylist = this.getPlaylistByName(
      "playlist-top-discoveries-for-year",
      `Highlights songs that ${user.name} first listened to (more than once) in 2021`
    );
    const topMissedRecordingsPlaylist = this.getPlaylistByName(
      "playlist-top-missed-recordings-for-year",
      `Favorite songs of ${user.name}'s most similar users that ${user.name} hasn't listened to this year`
    );
    const topNewRecordingsPlaylist = this.getPlaylistByName(
      "playlist-top-new-recordings-for-year",
      `Songs released in 2021 that ${user.name} listened to`
    );
    const topRecordingsPlaylist = this.getPlaylistByName(
      "playlist-top-recordings-for-year",
      `This playlist is made from ${user.name}'s top recordings for 2021 statistics`
    );
    if (
      !topDiscoveriesPlaylist ||
      !topMissedRecordingsPlaylist ||
      !topNewRecordingsPlaylist ||
      !topRecordingsPlaylist
    ) {
      missingSomeData = true;
    }

    const allPlaylists = [
      topDiscoveriesPlaylist,
      topMissedRecordingsPlaylist,
      topNewRecordingsPlaylist,
      topRecordingsPlaylist,
    ];

    const noDataText = (
      <div className="center-p">
        We were not able to calculate this data for {youOrUsername}
      </div>
    );
    return (
      <div role="main" id="year-in-music">
        <div className="flex flex-wrap" id="header">
          <div className="content-card flex-center flex-wrap">
            <img
              className="img-responsive header-image"
              src="/static/img/year-in-music-2021.svg"
              alt="Your year in music 2021"
            />
            <div>
              <h4>
                <div className="center-p">
                  Share your year with your friends
                  <p id="share-link">
                    <a
                      href={`https://listenbrainz.org/user/${user.name}/year-in-music/2021/`}
                    >
                      https://listenbrainz.org/user/{user.name}
                      /year-in-music/2021/
                    </a>
                  </p>
                </div>
              </h4>
            </div>
          </div>
          <div>
            <h1>
              {user.name}
              {currentUser?.name && !isCurrentUser && (
                <FollowButton
                  type="icon-only"
                  user={user}
                  loggedInUserFollowsUser={this.loggedInUserFollowsUser(user)}
                />
              )}
            </h1>
            <p>
              See profile on&nbsp;
              <img src="/static/img/favicon-16.png" alt="ListenBrainz Logo" />
              <a href={`https://listenbrainz.org/user/${user.name}/`}>
                ListenBrainz
              </a>
              &nbsp;and&nbsp;
              <img
                src="/static/img/musicbrainz-16.svg"
                alt="MusicBrainz Logo"
              />
              <a href={`https://musicbrainz.org/user/${user.name}`}>
                MusicBrainz
              </a>
            </p>
            <p>
              The ListenBrainz team would like to wish you happy holidays! You
              have been sending us your listen history in 2021 and we wanted to
              thank you for doing that! We have been working hard to create
              useful personalized features based on your data. We hope you like
              it!
            </p>
            <p>You will find in this page:</p>
            <ul>
              <li>
                {yourOrUsersName} top{" "}
                <a href="listenbrainz/webserver/static/js/src/year-in-music#top-releases">
                  albums
                </a>
                ,{" "}
                <a href="listenbrainz/webserver/static/js/src/year-in-music#top-recordings">
                  songs
                </a>{" "}
                and{" "}
                <a href="listenbrainz/webserver/static/js/src/year-in-music#top-artists">
                  artists
                </a>{" "}
                of the year
              </li>
              <li>
                some statistics about {yourOrUsersName}{" "}
                <a href="listenbrainz/webserver/static/js/src/year-in-music#calendar">
                  listening activity
                </a>
              </li>
              <li>
                a list of{" "}
                <a href="listenbrainz/webserver/static/js/src/year-in-music#similar-users">
                  users similar to {youOrUsername}
                </a>
              </li>
              <li>
                new albums that {yourOrUsersName} top artists{" "}
                <a href="listenbrainz/webserver/static/js/src/year-in-music#new-releases">
                  released in 2021
                </a>
              </li>
              <li>
                and finally four{" "}
                <a href="listenbrainz/webserver/static/js/src/year-in-music#playlists">
                  personalized playlists
                </a>
                &nbsp; of music {youOrUsername} listened to and new songs to
                discover
              </li>
            </ul>
            <p>
              Double click on any song to start playing it — we will do our best
              to find a matching song to play. If you have a Spotify pro
              account, we recommend{" "}
              <a href="/profile/music-services/details/">
                connecting your account
              </a>{" "}
              for a better playback experience.
            </p>
            <p>
              If you have questions or feedback don&apos;t hesitate to contact
              us on{" "}
              <a href="https://community.metabrainz.org/c/listenbrainz/18">
                our forums
              </a>
              , <a href="mailto:support@metabrainz.org">by email</a> or{" "}
              <a href="https://twitter.com/ListenBrainz">on twitter</a>
            </p>
            <p>
              We hope you like it! With love, the{" "}
              <a href="https://metabrainz.org/team">MetaBrainz team</a>
            </p>
          </div>
        </div>
        {missingSomeData && (
          <div className="alert alert-warning">
            Heads up: We were unable to compute all of the parts of Your Year in
            Music due to not enough listens or an issue in our database, but
            we&apos;re showing you everything that we were able to make. Your
            page might look a bit different than others.
          </div>
        )}
        <hr className="wide" />
        <div className="row">
          <div className="card content-card" id="top-releases">
            <div className="col-md-12 d-flex center-p">
              <h3>{capitalize(yourOrUsersName)} top albums of 2021</h3>
              {yearInMusicData.top_releases && (
                <ComponentToImage
                  data={yearInMusicData.top_releases
                    .filter((release) =>
                      has(
                        yearInMusicData.top_releases_coverart,
                        release.release_mbid
                      )
                    )
                    .slice(0, 10)
                    .map((release) => {
                      // eslint-disable-next-line no-param-reassign
                      release.cover_art_src =
                        yearInMusicData.top_releases_coverart?.[
                          release.release_mbid
                        ];
                      return release;
                    })}
                  entityType="release"
                  user={user}
                />
              )}
            </div>

            {yearInMusicData.top_releases ? (
              <div id="releases-coverflow">
                <Swiper
                  modules={[Navigation, Keyboard, EffectCoverflow]}
                  spaceBetween={15}
                  slidesPerView={2}
                  initialSlide={0}
                  centeredSlides
                  navigation
                  effect="coverflow"
                  coverflowEffect={{
                    rotate: 40,
                    depth: 100,
                    slideShadows: false,
                  }}
                  breakpoints={{
                    700: {
                      initialSlide: 3,
                      spaceBetween: 100,
                      slidesPerView: 3,
                      coverflowEffect: {
                        rotate: 20,
                        depth: 300,
                        slideShadows: false,
                      },
                    },
                  }}
                >
                  {yearInMusicData.top_releases.slice(0, 50).map((release) => {
                    const coverArtSrc =
                      yearInMusicData.top_releases_coverart?.[
                        release.release_mbid
                      ];
                    if (!coverArtSrc) {
                      return null;
                    }
                    return (
                      <SwiperSlide key={`coverflow-${release.release_name}`}>
                        <img
                          src={
                            yearInMusicData.top_releases_coverart?.[
                              release.release_mbid
                            ] ?? "/static/img/cover-art-placeholder.jpg"
                          }
                          alt={release.release_name}
                        />
                        <div title={release.release_name}>
                          <a
                            href={
                              release.release_mbid
                                ? `https://musicbrainz.org/release/${release.release_mbid}/`
                                : undefined
                            }
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {release.release_name}
                          </a>
                          <div className="small text-muted">
                            {release.artist_name}
                          </div>
                        </div>
                      </SwiperSlide>
                    );
                  })}
                </Swiper>
              </div>
            ) : (
              noDataText
            )}
          </div>
        </div>
        <div className="row flex flex-wrap">
          <div className="card content-card" id="top-recordings">
            <div className="col-md-12 d-flex center-p">
              <h3>
                {capitalize(yourOrUsersName)} 50 most played songs of 2021
              </h3>
              {yearInMusicData.top_recordings && (
                <ComponentToImage
                  data={yearInMusicData.top_recordings.slice(0, 10)}
                  entityType="recording"
                  user={user}
                />
              )}
            </div>
            {yearInMusicData.top_recordings ? (
              <div className="scrollable-area">
                {yearInMusicData.top_recordings
                  .slice(0, 50)
                  .map((recording) => {
                    const listenHere = {
                      listened_at: 0,
                      track_metadata: {
                        artist_name: recording.artist_name,
                        track_name: recording.track_name,
                        release_name: recording.release_name,
                        additional_info: {
                          recording_mbid: recording.recording_mbid,
                          release_mbid: recording.release_mbid,
                          artist_mbids: recording.artist_mbids,
                        },
                      },
                    };
                    listens.push(listenHere);
                    return (
                      <ListenCard
                        compact
                        key={`top-recordings-${recording.track_name}-${recording.recording_mbid}`}
                        listen={listenHere}
                        showTimestamp={false}
                        showUsername={false}
                        newAlert={newAlert}
                      />
                    );
                  })}
              </div>
            ) : (
              noDataText
            )}
          </div>
          <div className="card content-card" id="top-artists">
            <div className="col-md-12 d-flex center-p">
              <h3>{capitalize(yourOrUsersName)} top 50 artists of 2021</h3>
              {yearInMusicData.top_artists && (
                <ComponentToImage
                  data={yearInMusicData.top_artists.slice(0, 10)}
                  entityType="artist"
                  user={user}
                />
              )}
            </div>
            {yearInMusicData.top_artists ? (
              <div className="scrollable-area">
                {yearInMusicData.top_artists.slice(0, 50).map((artist) => {
                  const details = getEntityLink(
                    "artist",
                    artist.artist_name,
                    artist.artist_mbids[0]
                  );
                  const thumbnail = (
                    <span className="badge badge-info">
                      {artist.listen_count} listens
                    </span>
                  );
                  const listenHere = {
                    listened_at: 0,
                    track_metadata: {
                      track_name: "",
                      artist_name: artist.artist_name,
                      additional_info: {
                        artist_mbids: artist.artist_mbids,
                      },
                    },
                  };
                  listens.push(listenHere);
                  return (
                    <ListenCard
                      compact
                      key={`top-artists-${artist.artist_name}-${artist.artist_mbids}`}
                      listen={listenHere}
                      customThumbnail={thumbnail}
                      listenDetails={details}
                      showTimestamp={false}
                      showUsername={false}
                      newAlert={newAlert}
                    />
                  );
                })}
              </div>
            ) : (
              noDataText
            )}
          </div>
        </div>
        <div className="row">
          <div className="card content-card" id="calendar">
            <h3 className="text-center">
              {capitalize(yourOrUsersName)} listening activity in 2021
              <div className="small mt-15">
                Number of listens submitted for each day of the year
              </div>
            </h3>
            {listensPerDayForGraph ? (
              <div className="graph">
                <ResponsiveCalendar
                  from="2021-01-01"
                  to="2021-12-31"
                  data={listensPerDayForGraph as CalendarDatum[]}
                  emptyColor="#eeeeee"
                  colors={["#bbb7e1", "#6e66cc", "#eea582", COLOR_LB_ORANGE]}
                  monthBorderColor="#eeeeee"
                  dayBorderWidth={2}
                  dayBorderColor="#ffffff"
                  legends={[
                    {
                      anchor: "bottom-right",
                      direction: "row",
                      itemCount: 4,
                      itemWidth: 42,
                      itemHeight: 36,
                      itemsSpacing: 14,
                      itemDirection: "right-to-left",
                    },
                  ]}
                />
              </div>
            ) : (
              noDataText
            )}
          </div>
        </div>
        <div className="row flex flex-wrap">
          {yearInMusicData.total_listen_count && (
            <div className="card content-card">
              <h3 className="text-center">
                {capitalize(youOrUsername)} listened to{" "}
                <span className="accent">
                  {yearInMusicData.total_listen_count}
                </span>{" "}
                songs this year
              </h3>
            </div>
          )}
          {yearInMusicData.day_of_week && (
            <div className="card content-card">
              <h3 className="text-center">
                <span className="accent">{yearInMusicData.day_of_week}</span>{" "}
                was {yourOrUsersName} most active listening day on average
              </h3>
            </div>
          )}
        </div>
        <div className="row flex flex-wrap">
          <div className="card content-card" id="most-listened-year">
            <h3 className="text-center">
              What year are {yourOrUsersName} favorite songs from?
              <div className="small mt-15">
                How much were you on the lookout for new music this year? Not
                that we&apos;re judging.
              </div>
            </h3>
            {mostListenedYearDataForGraph ? (
              <div className="graph">
                <ResponsiveBar
                  margin={{ left: 50, bottom: 30 }}
                  data={mostListenedYearDataForGraph}
                  padding={0.1}
                  layout="vertical"
                  keys={["songs"]}
                  indexBy="year"
                  colors={COLOR_LB_ORANGE}
                  enableLabel={false}
                  axisBottom={{
                    // Round to nearest 5 year mark
                    tickValues: uniq(
                      mostListenedYearDataForGraph.map(
                        (datum) => Math.round((datum.year + 1) / 5) * 5
                      )
                    ),
                  }}
                  axisLeft={{
                    legend: "Number of listens",
                    legendOffset: -40,
                    legendPosition: "middle",
                  }}
                />
              </div>
            ) : (
              noDataText
            )}
          </div>
        </div>
        <div className="row flex flex-wrap">
          <div className="card content-card" id="similar-users">
            <h3 className="text-center">
              Music buddies
              <div className="small mt-15">
                Here are the users with the most similar taste to {user.name}{" "}
                this year. Maybe go check them out?
              </div>
            </h3>
            <div className="scrollable-area similar-users-list">
              {sortedSimilarUsers && sortedSimilarUsers.length
                ? sortedSimilarUsers.map((userFromList) => {
                    const [name, similarityScore] = userFromList;
                    const similarUser: SimilarUser = {
                      name,
                      similarityScore,
                    };
                    const loggedInUserFollowsUser = this.loggedInUserFollowsUser(
                      similarUser
                    );
                    return (
                      <UserListModalEntry
                        mode="similar-users"
                        key={name}
                        user={similarUser}
                        loggedInUserFollowsUser={loggedInUserFollowsUser}
                        updateFollowingList={this.updateFollowingList}
                      />
                    );
                  })
                : noDataText}
            </div>
          </div>

          <div className="card content-card" id="new-releases">
            <h3 className="text-center">
              New albums of {yourOrUsersName} top artists
              <div className="small mt-15">
                New albums released in 2021 from {yourOrUsersName} favorite
                artists
              </div>
            </h3>
            <div className="scrollable-area">
              {yearInMusicData.new_releases_of_top_artists
                ? yearInMusicData.new_releases_of_top_artists.map((release) => {
                    const artistName = release.artist_credit_names.join(", ");
                    const details = (
                      <>
                        <div title={release.title} className="ellipsis-2-lines">
                          {getEntityLink(
                            "release",
                            release.title,
                            release.release_mbid
                          )}
                        </div>
                        <span
                          className="small text-muted ellipsis"
                          title={artistName}
                        >
                          {getEntityLink(
                            "artist",
                            artistName,
                            release.artist_credit_mbids[0]
                          )}
                        </span>
                      </>
                    );
                    const listenHere = {
                      listened_at: 0,
                      listened_at_iso: release.first_release_date,
                      track_metadata: {
                        artist_name: artistName,
                        track_name: release.title,
                        release_name: release.title,
                        additional_info: {
                          release_mbid: release.release_mbid,
                          artist_mbids: release.artist_credit_mbids,
                        },
                      },
                    };
                    listens.push(listenHere);
                    return (
                      <ListenCard
                        listenDetails={details}
                        key={release.release_mbid}
                        compact
                        listen={listenHere}
                        showTimestamp={false}
                        showUsername={false}
                        newAlert={newAlert}
                      />
                    );
                  })
                : noDataText}
            </div>
          </div>
        </div>
        <div className="row">
          <div className="card content-card" id="playlists">
            <h3 className="text-center">
              We made some personalized playlists for {youOrUsername}!
              <div className="small mt-15">
                You&apos;ll find below 3 playlists that encapsulate{" "}
                {yourOrUsersName} year, and 1 playlist of music exploration
                based on users similar to {youOrUsername}
              </div>
            </h3>
            <div className="row flex flex-wrap">
              {allPlaylists.length
                ? allPlaylists.map((topLevelPlaylist) => {
                    if (!topLevelPlaylist) {
                      return undefined;
                    }
                    return (
                      <div
                        className="card content-card mb-10"
                        id="top-discoveries"
                      >
                        <h3 className="text-center">
                          <a
                            href={`/playlist/${topLevelPlaylist.mbid}`}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {topLevelPlaylist.jspf?.playlist?.title}
                          </a>
                          {topLevelPlaylist.description && (
                            <div className="small mt-15">
                              {topLevelPlaylist.description}
                            </div>
                          )}
                        </h3>
                        <div>
                          {topLevelPlaylist.jspf?.playlist?.track.map(
                            (playlistTrack) => {
                              const listen = JSPFTrackToListen(playlistTrack);
                              listens.push(listen);
                              let thumbnail;
                              if (playlistTrack.image) {
                                thumbnail = (
                                  <div className="listen-thumbnail">
                                    <img
                                      src={playlistTrack.image}
                                      alt={`Cover Art for ${playlistTrack.title}`}
                                    />
                                  </div>
                                );
                              }
                              return (
                                <ListenCard
                                  className="playlist-item-card"
                                  listen={listen}
                                  customThumbnail={thumbnail}
                                  compact
                                  showTimestamp={false}
                                  showUsername={false}
                                  newAlert={newAlert}
                                />
                              );
                            }
                          )}
                          <hr />
                          <a
                            href={`/playlist/${topLevelPlaylist.mbid}`}
                            className="btn btn-info btn-block"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            See the full playlist…
                          </a>
                        </div>
                      </div>
                    );
                  })
                : noDataText}
            </div>
          </div>
        </div>
        <hr className="wide" />
        <BrainzPlayer
          listens={listens}
          newAlert={newAlert}
          listenBrainzAPIBaseURI={APIService.APIBaseURI}
          refreshSpotifyToken={APIService.refreshSpotifyToken}
          refreshYoutubeToken={APIService.refreshYoutubeToken}
        />
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalAppContext,
    optionalAlerts,
  } = getPageProps();
  const { user, data: yearInMusicData } = reactProps;

  const YearInMusicWithAlertNotifications = withAlertNotifications(YearInMusic);

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <YearInMusicWithAlertNotifications
            user={user}
            yearInMusicData={yearInMusicData}
            initialAlerts={optionalAlerts}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
