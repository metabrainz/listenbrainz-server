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
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCopy,
  faQuestionCircle,
  faShareAlt,
} from "@fortawesome/free-solid-svg-icons";
import ErrorBoundary from "../../utils/ErrorBoundary";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../utils/GlobalAppContext";
import BrainzPlayer from "../../brainzplayer/BrainzPlayer";

import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../../notifications/AlertNotificationsHOC";

import APIServiceClass from "../../utils/APIService";
import {
  generateAlbumArtThumbnailLink,
  getAlbumArtFromReleaseMBID,
  getPageProps,
} from "../../utils/utils";
import { getEntityLink } from "../../stats/utils";
import MagicShareButton from "./MagicShareButton";

import ListenCard from "../../listens/ListenCard";
import UserListModalEntry from "../../follow/UserListModalEntry";
import {
  JSPFTrackToListen,
  MUSICBRAINZ_JSPF_TRACK_EXTENSION,
} from "../../playlists/utils";
import { COLOR_LB_ORANGE } from "../../utils/constants";
import SimpleModal from "../../utils/SimpleModal";

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
      caa_id?: number;
      caa_release_mbid?: string;
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
    new_releases_of_top_artists: Array<{
      title: string;
      release_group_mbid: string;
      caa_id?: number;
      caa_release_mbid?: string;
      artist_credit_mbids: string[];
      artist_credit_name: string;
    }>;
  };
} & WithAlertNotificationsInjectedProps;

export type YearInMusicState = {
  followingList: Array<string>;
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
    };
  }

  async componentDidMount() {
    await this.getFollowing();
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
    const listens: BaseListenFormat[] = [];

    if (!yearInMusicData || isEmpty(yearInMusicData)) {
      return (
        <div role="main" id="year-in-music" className="yim-2022">
          <div id="main-header" className="flex-center">
            <img
              className="img-responsive header-image"
              src="/static/img/year-in-music-22/logo-with-text.png"
              alt="Your year in music 2022"
              width="600"
            />
          </div>
          <div className="flex-center flex-wrap">
            <h3>
              We don&apos;t have enough listening data for {user.name} to
              produce any statistics or playlists.
            </h3>
            <p>
              Check out how you can submit listens by{" "}
              <a href="/profile/music-services/details/">
                connecting a music service
              </a>{" "}
              or <a href="/profile/import/">importing your listening history</a>
              , and come back next year!
            </p>
          </div>
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
      `Highlights songs that ${user.name} first listened to (more than once) in 2022`
    );
    const topMissedRecordingsPlaylist = this.getPlaylistByName(
      "playlist-top-missed-recordings-for-year",
      `Favorite songs of ${user.name}'s most similar users that ${user.name} hasn't listened to this year`
    );
    const topNewRecordingsPlaylist = this.getPlaylistByName(
      "playlist-top-new-recordings-for-year",
      `Songs released in 2022 that ${user.name} listened to`
    );
    const topRecordingsPlaylist = this.getPlaylistByName(
      "playlist-top-recordings-for-year",
      `This playlist is made from ${user.name}'s top recordings for 2022 statistics`
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
    const linkToThisPage = `https://listenbrainz.org/user/${user.name}/year-in-music/`;
    return (
      <div role="main" id="year-in-music" className="yim-2022">
        <div id="header" className="flex-center">
          <img
            className="img-responsive header-image"
            src="/static/img/year-in-music-22/yim22-logo.png"
            alt="Your year in music 2022"
          />
        </div>
        <div className="red-section">
          <div className="container share-section flex-center">
            <div>
              Share <b>{yourOrUsersName}</b> year
              <div className="input-group">
                <input
                  type="text"
                  className="form-control"
                  disabled
                  size={linkToThisPage.length - 5}
                  value={linkToThisPage}
                />
                <span className="input-group-addon">
                  <FontAwesomeIcon
                    icon={faCopy}
                    onClick={async () => {
                      await navigator.clipboard.writeText(linkToThisPage);
                    }}
                  />
                </span>
                <span className="input-group-addon">
                  <FontAwesomeIcon icon={faShareAlt} />
                </span>
              </div>
            </div>
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
        <div className="yellow-section">
          <div className="container">
            <div className="card content-card" id="top-releases">
              <div className="col-md-12 d-flex center-p">
                <h3>Top albums of 2022</h3>
              </div>

              {yearInMusicData.top_releases ? (
                <div id="top-albums">
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
                    {yearInMusicData.top_releases
                      .slice(0, 50)
                      .map((release) => {
                        if (!release.caa_id || !release.caa_release_mbid) {
                          return null;
                        }
                        const coverArt = generateAlbumArtThumbnailLink(
                          release.caa_id,
                          release.caa_release_mbid
                        );
                        return (
                          <SwiperSlide
                            key={`coverflow-${release.release_name}`}
                          >
                            <img
                              src={
                                coverArt ??
                                "/static/img/cover-art-placeholder.jpg"
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
            <div className="share-button-container">
              <MagicShareButton
                svgURL={`https://api.listenbrainz.org/1/art/grid-stats/${user.name}/year/4/0/500`}
                shareUrl={`${linkToThisPage}#top-albums`}
                // shareText="Check out my"
                shareTitle="My top albums of 2022"
                fileName={`${user.name}-top-albums-2022`}
              />
            </div>
          </div>
        </div>
        <div className="red-section">
          <div className="container">
            <div className="header">
              Charts
              <div className="subheader">
                These got you through the year. Respect.
              </div>
            </div>
            <div className="flex flex-wrap">
              <div style={{ display: "table" }}>
                <div className="card content-card" id="top-tracks">
                  <div className="center-p">
                    <img
                      className="img-header"
                      src="/static/img/year-in-music-22/stereo.png"
                      alt="Top artists of 2022"
                    />
                    <h4>Top tracks of 2022</h4>
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
                <div className="share-button-container">
                  <MagicShareButton
                    svgURL={`https://api.listenbrainz.org/1/art/designer-top-10/${user.name}/year/500`}
                    shareUrl={`${linkToThisPage}#top-tracks`}
                    // shareText="Check out my"
                    shareTitle="My top tracks of 2022"
                    fileName={`${user.name}-top-tracks-2022`}
                  />
                </div>
              </div>
              <div style={{ display: "table" }}>
                <div className="card content-card" id="top-artists">
                  <div className="center-p">
                    <img
                      className="img-header"
                      src="/static/img/year-in-music-22/map.png"
                      alt="Top artists of 2022"
                    />
                    <h4>Top artists of 2022</h4>
                  </div>
                  {yearInMusicData.top_artists ? (
                    <div className="scrollable-area">
                      {yearInMusicData.top_artists
                        .slice(0, 50)
                        .map((artist) => {
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
                <div className="share-button-container">
                  <MagicShareButton
                    svgURL={`https://api.listenbrainz.org/1/art/designer-top-5/${user.name}/year/500`}
                    shareUrl={`${linkToThisPage}#top-artists`}
                    // shareText="Check out my"
                    shareTitle="My top artists of 2022"
                    fileName={`${user.name}-top-artists-2022`}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="yellow-section">
          <div className="container">
            <div className="header">
              Statistics
              <div className="subheader">Mmmm…Delicous.</div>
            </div>
            <div className="card content-card" id="calendar">
              <h3 className="text-center">
                {capitalize(yourOrUsersName)} listening activity
              </h3>
              {listensPerDayForGraph ? (
                <div className="graph">
                  <ResponsiveCalendar
                    from="2022-01-01"
                    to="2022-12-31"
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
            <div className="flex flex-wrap small-cards-container">
              {yearInMusicData.total_listen_count && (
                <div className="card content-card">
                  <div className="text-center">
                    {capitalize(youOrUsername)} listened to{" "}
                    <span className="accent">
                      {yearInMusicData.total_listen_count}
                    </span>{" "}
                    songs this year
                  </div>
                </div>
              )}
              {yearInMusicData.day_of_week && (
                <div className="card content-card">
                  <div className="text-center">
                    <span className="accent">
                      {yearInMusicData.day_of_week}
                    </span>{" "}
                    was {yourOrUsersName} most active listening day on average
                  </div>
                </div>
              )}
            </div>
            <div className="card content-card" id="most-listened-year">
              <h3 className="text-center">
                What year are {yourOrUsersName} favorite songs from?
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
        </div>
        <div className="red-section">
          <div className="container">
            <div className="header">
              2022 Playlists
              <div className="subheader">Generated just for you.</div>
            </div>
            <div className="row flex flex-wrap" id="playlists">
              {allPlaylists.length
                ? allPlaylists.slice(0, 2).map((topLevelPlaylist) => {
                    if (!topLevelPlaylist) {
                      return undefined;
                    }
                    return (
                      <div
                        className="card content-card mb-10"
                        id="top-discoveries"
                      >
                        <div className="center-p">
                          SVG OF COVERS HERE
                          <h4>
                            <a
                              href={`/playlist/${topLevelPlaylist.mbid}`}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {topLevelPlaylist.jspf?.playlist?.title}
                            </a>
                            <FontAwesomeIcon icon={faQuestionCircle} />
                            {/* {topLevelPlaylist.description} */}
                          </h4>
                        </div>
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
        <div className="yellow-section">
          <div className="container">
            <div className="header">
              Discover
              <div className="subheader">
                The year&apos;s over, but there&apos;s still more to uncover!
              </div>
            </div>
            <div className="flex flex-wrap">
              <div
                className="card content-card"
                id="new-releases"
                style={{ marginBottom: "2.5em" }}
              >
                <div className="center-p">
                  <img
                    className="img-header"
                    src="/static/img/year-in-music-22/magnify.png"
                    alt={`New albums from ${yourOrUsersName} top artists`}
                  />
                  <h4>New albums from {yourOrUsersName} top artists</h4>
                </div>
                <div className="scrollable-area">
                  {yearInMusicData.new_releases_of_top_artists
                    ? yearInMusicData.new_releases_of_top_artists.map(
                        (release) => {
                          const details = (
                            <>
                              <div
                                title={release.title}
                                className="ellipsis-2-lines"
                              >
                                {getEntityLink(
                                  "release-group",
                                  release.title,
                                  release.release_group_mbid
                                )}
                              </div>
                              <span
                                className="small text-muted ellipsis"
                                title={release.artist_credit_name}
                              >
                                {getEntityLink(
                                  "artist",
                                  release.artist_credit_name,
                                  release.artist_credit_mbids[0]
                                )}
                              </span>
                            </>
                          );
                          const listenHere: Listen = {
                            listened_at: 0,
                            track_metadata: {
                              artist_name: release.artist_credit_name,
                              track_name: release.title,
                              release_name: release.title,
                              additional_info: {
                                release_group_mbid: release.release_group_mbid,
                                artist_mbids: release.artist_credit_mbids,
                              },
                              mbid_mapping: {
                                recording_mbid: "",
                                release_mbid: "",
                                artist_mbids: [],
                                caa_id: release.caa_id,
                                caa_release_mbid: release.caa_release_mbid,
                              },
                            },
                          };
                          listens.push(listenHere);
                          return (
                            <ListenCard
                              listenDetails={details}
                              key={release.release_group_mbid}
                              compact
                              listen={listenHere}
                              showTimestamp={false}
                              showUsername={false}
                              newAlert={newAlert}
                            />
                          );
                        }
                      )
                    : noDataText}
                </div>
              </div>

              <div
                className="card content-card"
                id="similar-users"
                style={{ marginBottom: "2.5em" }}
              >
                <div className="center-p">
                  <img
                    className="img-header"
                    src="/static/img/year-in-music-22/buddy.png"
                    alt="Music buddies"
                  />
                  <h4>Music buddies</h4>
                </div>
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
            </div>
          </div>
        </div>
        <div className="red-section cover-art-composite">
          <div className="container">
            <div className="header">
              2022 Albums
              <div className="subheader">
                Just some of the albums that came out in 2022. Drag, scroll and
                click to listen to an album.
              </div>
            </div>
          </div>
          <img
            src="https://via.placeholder.com/1800x600?text=Cover+art+composite+image+here"
            alt="2022 albums"
          />
        </div>
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
  const { domContainer, reactProps, globalReactProps } = getPageProps();
  const { api_url, current_user, spotify, youtube } = globalReactProps;
  const { user, data: yearInMusicData } = reactProps;

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const YearInMusicWithAlertNotifications = withAlertNotifications(YearInMusic);

  const modalRef = React.createRef<SimpleModal>();
  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
    modal: modalRef,
  };

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <SimpleModal ref={modalRef} />
      <GlobalAppContext.Provider value={globalProps}>
        <YearInMusicWithAlertNotifications
          user={user}
          yearInMusicData={yearInMusicData}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
