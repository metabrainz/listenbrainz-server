import * as React from "react";
import { ResponsiveBar } from "@nivo/bar";
import { Navigation, Keyboard, EffectCoverflow, Lazy } from "swiper";
import { Swiper, SwiperSlide } from "swiper/react";
import { CalendarDatum, ResponsiveCalendar } from "@nivo/calendar";
import Tooltip from "react-tooltip";
import { toast } from "react-toastify";
import {
  get,
  isEmpty,
  isNil,
  range,
  uniq,
  capitalize,
  toPairs,
  isUndefined,
} from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCopy,
  faHeadphones,
  faQuestionCircle,
  faShareAlt,
} from "@fortawesome/free-solid-svg-icons";
import { LazyLoadImage } from "react-lazy-load-image-component";
import { Link, useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import GlobalAppContext from "../../../utils/GlobalAppContext";

import { generateAlbumArtThumbnailLink } from "../../../utils/utils";
import { getEntityLink } from "../../stats/utils";
import MagicShareButton from "./components/MagicShareButton";

import ListenCard from "../../../common/listens/ListenCard";
import UserListModalEntry from "../../components/follow/UserListModalEntry";
import { JSPFTrackToListen } from "../../../playlists/utils";
import { COLOR_LB_ORANGE } from "../../../utils/constants";
import CustomChoropleth from "../../stats/components/Choropleth";
import { ToastMsg } from "../../../notifications/Notifications";
import SEO, { YIMYearMetaTags } from "../SEO";
import { RouteQuery } from "../../../utils/Loader";
import { useBrainzPlayerDispatch } from "../../../common/brainzplayer/BrainzPlayerContext";

export type YearInMusicProps = {
  user: ListenBrainzUser;
  yearInMusicData?: {
    day_of_week: string;
    top_artists: Array<{
      artist_name: string;
      artist_mbid: string;
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
    artist_map: Array<{
      country: string;
      artist_count: number;
      listen_count: number;
      artists: Array<UserArtistMapArtist>;
    }>;
  };
  topDiscoveriesPlaylist: JSPFPlaylist | undefined;
  topMissedRecordingsPlaylist: JSPFPlaylist | undefined;
  missingSomePlaylistData: boolean;
  hasNoPlaylists: boolean;
};

type YearInMusicLoaderData = {
  user: YearInMusicProps["user"];
  data: YearInMusicProps["yearInMusicData"];
};

export type YearInMusicState = {
  followingList: Array<string>;
  selectedMetric: "artist" | "listen";
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
      selectedMetric: "listen",
    };
  }

  async componentDidMount() {
    await this.getFollowing();
  }

  async componentDidUpdate(prevProps: YearInMusicProps) {
    const { user } = this.props;
    if (user !== prevProps.user) {
      await this.getFollowing();
    }
  }

  private getPlaylistByName(
    playlistName: string,
    description?: string
  ): JSPFPlaylist | undefined {
    const uuidMatch = /[0-9a-f]{8}\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\b[0-9a-f]{12}/g;
    const { yearInMusicData } = this.props;
    let playlist;
    try {
      playlist = get(yearInMusicData, playlistName);
      if (!playlist) {
        return undefined;
      }
      const coverArt = get(yearInMusicData, `${playlistName}-coverart`);
      // Append manual description used in this page (rather than parsing HTML, ellipsis issues, etc.)
      if (description) {
        playlist.annotation = description;
      }
      /* Add a track image if it exists in the `{playlistName}-coverart` key */
      playlist.track = playlist.track.map((track: JSPFTrack) => {
        const newTrack = { ...track };
        let track_id;
        if (Array.isArray(track.identifier)) {
          // eslint-disable-next-line prefer-destructuring
          track_id = track.identifier[0];
        } else {
          track_id = track.identifier;
        }
        const found = track_id.match(uuidMatch);
        if (found) {
          const recording_mbid = found[0];
          newTrack.id = recording_mbid;
          const recording_coverart = coverArt?.[recording_mbid];
          if (recording_coverart) {
            newTrack.image = recording_coverart;
          }
        }
        return newTrack;
      });
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error(`"Error parsing ${playlistName}:`, error);
      return undefined;
    }
    return playlist;
  }

  changeSelectedMetric = (
    newSelectedMetric: "artist" | "listen",
    event?: React.MouseEvent<HTMLElement>
  ) => {
    if (event) {
      event.preventDefault();
    }

    this.setState({
      selectedMetric: newSelectedMetric,
    });
  };

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
      toast.error(
        <ToastMsg
          title="Error while fetching the users you follow"
          message={err.toString()}
        />,
        { toastId: "fetch-following-error" }
      );
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

  sharePage = () => {
    const dataToShare: ShareData = {
      title: "My 2022 in music",
      url: window.location.toString(),
    };
    // Use the Share API to share the image
    if (navigator.canShare && navigator.canShare(dataToShare)) {
      navigator.share(dataToShare).catch((error) => {
        toast.error(
          <ToastMsg title="Error sharing image" message={error.toString()} />,
          { toastId: "sharing-image-error" }
        );
      });
    }
  };

  showTopLevelPlaylist = (
    index: number,
    topLevelPlaylist: JSPFPlaylist | undefined,
    coverArtKey: string
  ): JSX.Element | undefined => {
    if (!topLevelPlaylist) {
      return undefined;
    }
    const { APIService } = this.context;
    const { user } = this.props;
    return (
      <div className="card content-card mb-10" id={`${coverArtKey}`}>
        <div className="center-p">
          <object
            style={{ maxWidth: "100%" }}
            data={`${APIService.APIBaseURI}/art/year-in-music/2022/${user.name}?image=${coverArtKey}`}
          >{`SVG of cover art for Top Discovery Playlist for ${user.name}`}</object>
          <h4>
            <a
              href={topLevelPlaylist.identifier}
              target="_blank"
              rel="noopener noreferrer"
            >
              {topLevelPlaylist.title}{" "}
            </a>
            <FontAwesomeIcon
              icon={faQuestionCircle}
              data-tip
              data-for={`playlist-${index}-tooltip`}
              size="xs"
            />
            <Tooltip id={`playlist-${index}-tooltip`}>
              {topLevelPlaylist.annotation}
            </Tooltip>
          </h4>
        </div>
        <div>
          {topLevelPlaylist.track.slice(0, 5).map((playlistTrack) => {
            const listen = JSPFTrackToListen(playlistTrack);
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
              />
            );
          })}
          <hr />
          <a
            href={topLevelPlaylist.identifier}
            className="btn btn-info btn-block"
            target="_blank"
            rel="noopener noreferrer"
          >
            See the full playlist…
          </a>
        </div>
      </div>
    );
  };

  render() {
    const {
      user,
      yearInMusicData,
      topDiscoveriesPlaylist,
      topMissedRecordingsPlaylist,
      missingSomePlaylistData,
      hasNoPlaylists,
    } = this.props;
    const { selectedMetric } = this.state;
    const { APIService, currentUser } = this.context;

    if (!yearInMusicData || isEmpty(yearInMusicData)) {
      return (
        <div id="year-in-music" className="yim-2022 container">
          <SEO year={2022} userName={user?.name} />
          <YIMYearMetaTags year={2022} />
          <div id="main-header" className="flex-center">
            <img
              className="img-responsive header-image"
              src="/static/img/year-in-music-22/yim22-logo.png"
              alt="Your year in music 2022"
            />
          </div>
          <div>
            <h3 className="center-p">
              We don&apos;t have enough listening data for {user.name} to
              produce any statistics or playlists.
            </h3>
            <p className="center-p">
              Check out how you can submit listens by{" "}
              <Link to="/settings/music-services/details/">
                connecting a music service
              </Link>{" "}
              or{" "}
              <Link to="/settings/import/">
                importing your listening history
              </Link>
              , and come back next year!
            </p>
          </div>
        </div>
      );
    }

    // Some data might not have been calculated for some users
    // This boolean lets us warn them of that
    let missingSomeData = missingSomePlaylistData;

    if (
      !yearInMusicData.top_releases ||
      !yearInMusicData.top_recordings ||
      !yearInMusicData.top_artists ||
      !yearInMusicData.listens_per_day ||
      !yearInMusicData.total_listen_count ||
      !yearInMusicData.day_of_week ||
      !yearInMusicData.new_releases_of_top_artists ||
      !yearInMusicData.artist_map
    ) {
      missingSomeData = true;
    }

    // Is the logged-in user looking at their own page?
    const isCurrentUser = user.name === currentUser?.name;
    const youOrUsername = isCurrentUser ? "you" : `${user.name}`;
    const yourOrUsersName = isCurrentUser ? "your" : `${user.name}'s`;

    /* Most listened years */
    let mostListenedYearDataForGraph;
    let mostListenedYearTicks;
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
      // Round to nearest 5 year mark but don't add dates that are out of the range of the listening history
      const mostListenedYearYears = uniq(
        mostListenedYearDataForGraph.map((datum) => datum.year)
      );
      const mostListenedMaxYear = Math.max(...mostListenedYearYears);
      const mostListenedMinYear = Math.min(...mostListenedYearYears);
      mostListenedYearTicks = uniq(
        mostListenedYearYears
          .map((year) => Math.round((year + 1) / 5) * 5)
          .filter(
            (year) => year >= mostListenedMinYear && year <= mostListenedMaxYear
          )
      );
    }

    /* Users artist map */
    let artistMapDataForGraph;
    if (isEmpty(yearInMusicData.artist_map)) {
      missingSomeData = true;
    } else {
      artistMapDataForGraph = yearInMusicData.artist_map.map((country) => ({
        id: country.country,
        value:
          selectedMetric === "artist"
            ? country.artist_count
            : country.listen_count,
        artists: country.artists,
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

    const noDataText = (
      <div className="center-p no-data">
        We were not able to calculate this data for {youOrUsername}
      </div>
    );
    const linkToThisPage = `https://listenbrainz.org/user/${user.name}/year-in-music/2022`;
    return (
      <div id="year-in-music" className="yim-2022">
        <SEO year={2022} userName={user?.name} />
        <YIMYearMetaTags year={2022} />
        <div id="main-header" className="flex-center">
          <img
            className="img-responsive header-image"
            src="/static/img/year-in-music-22/yim22-logo.png"
            alt="Your year in music 2022"
          />
          <div className="arrow-down" />
        </div>
        <div className="red-section">
          <div className="link-section flex-center">
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
                {!isUndefined(navigator.canShare) ? (
                  <span className="input-group-addon">
                    <FontAwesomeIcon
                      icon={faShareAlt}
                      onClick={this.sharePage}
                    />
                  </span>
                ) : null}
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
            <div className="header">Top albums of 2022</div>
            <div className="card content-card" id="top-releases">
              {yearInMusicData.top_releases ? (
                <div id="top-albums">
                  <Swiper
                    modules={[Navigation, Keyboard, EffectCoverflow, Lazy]}
                    spaceBetween={15}
                    slidesPerView={2}
                    initialSlide={0}
                    centeredSlides
                    lazy={{
                      enabled: true,
                      loadPrevNext: true,
                      loadPrevNextAmount: 4,
                    }}
                    watchSlidesProgress
                    navigation
                    effect="coverflow"
                    coverflowEffect={{
                      rotate: 40,
                      depth: 100,
                      slideShadows: false,
                    }}
                    breakpoints={{
                      700: {
                        initialSlide: 2,
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
                              data-src={
                                coverArt ??
                                "/static/img/cover-art-placeholder.jpg"
                              }
                              alt={release.release_name}
                              className="swiper-lazy"
                            />
                            <div className="swiper-lazy-preloader swiper-lazy-preloader-white" />
                            <div title={release.release_name}>
                              {release.release_mbid ? (
                                <Link to={`/release/${release.release_mbid}/`}>
                                  {release.release_name}
                                </Link>
                              ) : (
                                release.release_name
                              )}
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
            <div className="yim-share-button-container">
              <MagicShareButton
                svgURL={`${APIService.APIBaseURI}/art/year-in-music/2022/${user.name}?image=albums`}
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
                These got {youOrUsername} through the year. Respect.
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
                          return (
                            <ListenCard
                              compact
                              key={`top-recordings-${recording.track_name}-${recording.recording_mbid}`}
                              listen={listenHere}
                              showTimestamp={false}
                              showUsername={false}
                            />
                          );
                        })}
                    </div>
                  ) : (
                    noDataText
                  )}
                </div>
                <div className="yim-share-button-container">
                  <MagicShareButton
                    svgURL={`${APIService.APIBaseURI}/art/year-in-music/2022/${user.name}?image=tracks`}
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
                            artist.artist_mbid
                          );
                          const thumbnail = (
                            <span className="badge badge-info">
                              <FontAwesomeIcon
                                style={{ marginRight: "4px" }}
                                icon={faHeadphones}
                              />{" "}
                              {artist.listen_count}
                            </span>
                          );
                          const listenHere = {
                            listened_at: 0,
                            track_metadata: {
                              track_name: "",
                              artist_name: artist.artist_name,
                              additional_info: {
                                artist_mbids: [artist.artist_mbid],
                              },
                            },
                          };
                          return (
                            <ListenCard
                              compact
                              key={`top-artists-${artist.artist_name}-${artist.artist_mbid}`}
                              listen={listenHere}
                              customThumbnail={thumbnail}
                              listenDetails={details}
                              showTimestamp={false}
                              showUsername={false}
                            />
                          );
                        })}
                    </div>
                  ) : (
                    noDataText
                  )}
                </div>
                <div className="yim-share-button-container">
                  <MagicShareButton
                    svgURL={`${APIService.APIBaseURI}/art/year-in-music/2022/${user.name}?image=artists`}
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
          <div className="container" id="stats">
            <div className="header">
              Statistics
              <div className="subheader">Mmmm…Delicous.</div>
            </div>
            <div className="yim-share-button-container">
              <MagicShareButton
                svgURL={`${APIService.APIBaseURI}/art/year-in-music/2022/${user.name}?image=stats`}
                shareUrl={`${linkToThisPage}#stats`}
                shareTitle="My music listening in 2022"
                fileName={`${user.name}-stats-2022`}
              />
            </div>
            <div className="card content-card" id="calendar">
              <h3 className="text-center">
                {capitalize(yourOrUsersName)} listening activity{" "}
                <FontAwesomeIcon
                  icon={faQuestionCircle}
                  data-tip
                  data-for="listening-activity"
                  size="xs"
                />
                <Tooltip id="listening-activity">
                  How many tracks did {youOrUsername} listen to each day of the
                  year?
                </Tooltip>
              </h3>
              {listensPerDayForGraph ? (
                <div className="graph-container">
                  <div className="graph">
                    <ResponsiveCalendar
                      from="2022-01-01"
                      to="2022-12-31"
                      data={listensPerDayForGraph as CalendarDatum[]}
                      emptyColor="#eeeeee"
                      colors={[
                        "#f9e5b3",
                        "#ffcc49",
                        COLOR_LB_ORANGE,
                        "#ff0e25",
                      ]}
                      monthBorderColor="#eeeeee"
                      dayBorderWidth={1}
                      dayBorderColor="#ffffff"
                      legends={[
                        {
                          anchor: "bottom-left",
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
                What year are {yourOrUsersName} favorite songs from?{" "}
                <FontAwesomeIcon
                  icon={faQuestionCircle}
                  data-tip
                  data-for="most-listened-year-helptext"
                  size="xs"
                />
                <Tooltip id="most-listened-year-helptext">
                  How much {isCurrentUser ? "were you" : `was ${user.name}`} on
                  the lookout for new music this year? Not that we&apos;re
                  judging.
                </Tooltip>
              </h3>
              {mostListenedYearDataForGraph ? (
                <div className="graph-container">
                  <div className="graph">
                    <ResponsiveBar
                      margin={{ left: 50, bottom: 30 }}
                      data={mostListenedYearDataForGraph}
                      padding={0.1}
                      layout="vertical"
                      keys={["songs"]}
                      indexBy="year"
                      colors="#ff0e25"
                      enableLabel={false}
                      axisBottom={{
                        tickValues: mostListenedYearTicks,
                      }}
                      axisLeft={{
                        legend: "Number of listens",
                        legendOffset: -40,
                        legendPosition: "middle",
                      }}
                    />
                  </div>
                </div>
              ) : (
                noDataText
              )}
            </div>
            <div
              className="card content-card"
              id="user-artist-map"
              style={{ marginTop: "1.5em" }}
            >
              <h3 className="text-center">
                What countries are {yourOrUsersName} favorite artists from?{" "}
                <FontAwesomeIcon
                  icon={faQuestionCircle}
                  data-tip
                  data-for="user-artist-map-helptext"
                  size="xs"
                />
                <Tooltip id="user-artist-map-helptext">
                  Click on a country to see more details
                </Tooltip>
              </h3>
              {artistMapDataForGraph ? (
                <div className="graph-container">
                  <div className="graph">
                    <div style={{ paddingLeft: "3em" }}>
                      <span>Rank by number of</span>
                      <span className="dropdown">
                        <button
                          className="dropdown-toggle btn-transparent capitalize-bold"
                          data-toggle="dropdown"
                          type="button"
                        >
                          {selectedMetric}s
                          <span className="caret" />
                        </button>
                        <ul className="dropdown-menu" role="menu">
                          <li
                            className={
                              selectedMetric === "listen" ? "active" : undefined
                            }
                          >
                            {/* eslint-disable-next-line jsx-a11y/anchor-is-valid */}
                            <a
                              href=""
                              role="button"
                              onClick={(event) =>
                                this.changeSelectedMetric("listen", event)
                              }
                            >
                              Listens
                            </a>
                          </li>
                          <li
                            className={
                              selectedMetric === "artist" ? "active" : undefined
                            }
                          >
                            {/* eslint-disable-next-line jsx-a11y/anchor-is-valid */}
                            <a
                              href=""
                              role="button"
                              onClick={(event) =>
                                this.changeSelectedMetric("artist", event)
                              }
                            >
                              Artists
                            </a>
                          </li>
                        </ul>
                      </span>
                    </div>
                    <CustomChoropleth
                      data={artistMapDataForGraph}
                      selectedMetric={selectedMetric}
                      colorScaleRange={[
                        "#ffeec2",
                        "#ffdb80",
                        "#ffcc49",
                        "#ff9c40",
                        "#ff6b36",
                        "#ff0a23",
                      ]}
                    />
                  </div>
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
              <div className="subheader">
                Generated just for {youOrUsername}.
              </div>
            </div>
            <div className="row flex flex-wrap" id="playlists">
              {Boolean(topDiscoveriesPlaylist) &&
                this.showTopLevelPlaylist(
                  0,
                  topDiscoveriesPlaylist,
                  "discovery-playlist"
                )}
              {Boolean(topMissedRecordingsPlaylist) &&
                this.showTopLevelPlaylist(
                  1,
                  topMissedRecordingsPlaylist,
                  "missed-playlist"
                )}
              {hasNoPlaylists && noDataText}
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
                  <h4>
                    New albums from {yourOrUsersName} top artists{" "}
                    <FontAwesomeIcon
                      icon={faQuestionCircle}
                      data-tip
                      data-for="new-albums-helptext"
                      size="xs"
                    />
                    <Tooltip id="new-albums-helptext">
                      Albums and singles released in 2022 from artists{" "}
                      {youOrUsername} listened to.
                      <br />
                      Missed anything?
                    </Tooltip>
                  </h4>
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
                          return (
                            <ListenCard
                              listenDetails={details}
                              key={release.release_group_mbid}
                              compact
                              listen={listenHere}
                              showTimestamp={false}
                              showUsername={false}
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
                  <h4>
                    Music buddies{" "}
                    <FontAwesomeIcon
                      icon={faQuestionCircle}
                      data-tip
                      data-for="music-buddies-helptext"
                      size="xs"
                    />
                    <Tooltip id="music-buddies-helptext">
                      Here are the users with the most similar taste to{" "}
                      {youOrUsername} this year.
                      <br />
                      Maybe check them out and follow them?
                    </Tooltip>
                  </h4>
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
                An interactive collage of albums released in 2022. Drag, scroll,
                and click to explore.
              </div>
            </div>
          </div>
          <div className="composite-image">
            <Link to="/explore/cover-art-collage/2022/">
              <LazyLoadImage
                src="https://staticbrainz.org/LB/year-in-music/2022/rainbow1-100-7-small.jpeg"
                placeholderSrc="https://staticbrainz.org/LB/year-in-music/2022/rainbow1-100-7-small.jpeg"
                srcSet="https://staticbrainz.org/LB/year-in-music/2022/rainbow1-100-7-small.jpeg 500w,
                https://staticbrainz.org/LB/year-in-music/2022/rainbow1-100-7-medium.jpeg 1000w,
                https://staticbrainz.org/LB/year-in-music/2022/rainbow1-100-7-large.jpeg 2000w"
                alt="2022 albums"
                loading="lazy"
                decoding="async"
              />
            </Link>
          </div>
          <div className="container closing-remarks">
            <span className="bold">
              Wishing you a wonderful 2023, from the ListenBrainz team.
            </span>
            <br />
            If you have questions or feedback don&apos;t hesitate to contact us
            <br />
            on{" "}
            <a
              target="_blank"
              href="https://community.metabrainz.org/c/listenbrainz/18"
              rel="noopener noreferrer"
            >
              our forums
            </a>
            ,{" "}
            <a
              target="_blank"
              href="mailto:listenbrainz@metabrainz.org"
              rel="noopener noreferrer"
            >
              by email
            </a>
            ,{" "}
            <a
              target="_blank"
              href="https://web.libera.chat/#metabrainz"
              rel="noopener noreferrer"
            >
              IRC
            </a>
            , or{" "}
            <a
              target="_blank"
              href="https://twitter.com/listenbrainz"
              rel="noopener noreferrer"
            >
              on twitter
            </a>{" "}
            <br />
            <br />
            Feeling nostalgic? See your previous Year in Music:{" "}
            <Link to={`/user/${user.name}/year-in-music/2021/`}>2021</Link>
          </div>
          <div className="thanks-kc-green">
            With thanks to KC Green for the original &apos;this is fine&apos;
            cartoon.
          </div>
        </div>
      </div>
    );
  }
}

export function YearInMusicWrapper() {
  const location = useLocation();
  const params = useParams();
  const { data } = useQuery<YearInMusicLoaderData>(
    RouteQuery(["year-in-music-2022", params], location.pathname)
  );
  const fallbackUser = { name: "" };
  const { user = fallbackUser, data: yearInMusicData } = data || {};
  const listens: BaseListenFormat[] = [];

  if (yearInMusicData?.top_recordings) {
    yearInMusicData.top_recordings.forEach((recording) => {
      const listen = {
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
      listens.push(listen);
    });
  }

  function getPlaylistByName(
    playlistName: string,
    description?: string
  ): JSPFPlaylist | undefined {
    const uuidMatch = /[0-9a-f]{8}\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\b[0-9a-f]{12}/g;
    let playlist;
    try {
      playlist = get(yearInMusicData, playlistName);
      if (!playlist) {
        return undefined;
      }
      const coverArt = get(yearInMusicData, `${playlistName}-coverart`);
      // Append manual description used in this page (rather than parsing HTML, ellipsis issues, etc.)
      if (description) {
        playlist.annotation = description;
      }
      /* Add a track image if it exists in the `{playlistName}-coverart` key */
      playlist.track = playlist.track.map((track: JSPFTrack) => {
        const newTrack = { ...track };
        const track_id = Array.isArray(track.identifier)
          ? track.identifier[0]
          : track.identifier;
        const found = track_id.match(uuidMatch);
        if (found) {
          const recording_mbid = found[0];
          newTrack.id = recording_mbid;
          const recording_coverart = coverArt?.[recording_mbid];
          if (recording_coverart) {
            newTrack.image = recording_coverart;
          }
        }
        return newTrack;
      });
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error(`"Error parsing ${playlistName}:`, error);
      return undefined;
    }
    return playlist;
  }

  /* Playlists */
  let missingSomePlaylistData = false;
  let hasNoPlaylists = false;
  const topDiscoveriesPlaylist = getPlaylistByName(
    "playlist-top-discoveries-for-year",
    `Highlights songs that ${user.name} first listened to (more than once) in 2022`
  );
  const topMissedRecordingsPlaylist = getPlaylistByName(
    "playlist-top-missed-recordings-for-year",
    `Favorite songs of ${user.name}'s most similar users that ${user.name} hasn't listened to this year`
  );
  if (!topDiscoveriesPlaylist || !topMissedRecordingsPlaylist) {
    missingSomePlaylistData = true;
  }
  if (!topDiscoveriesPlaylist && !topMissedRecordingsPlaylist) {
    hasNoPlaylists = true;
  }

  if (topDiscoveriesPlaylist) {
    topDiscoveriesPlaylist.track.slice(0, 5).forEach((playlistTrack) => {
      const listen = JSPFTrackToListen(playlistTrack);
      listens.push(listen);
    });
  }

  if (topMissedRecordingsPlaylist) {
    topMissedRecordingsPlaylist.track.slice(0, 5).forEach((playlistTrack) => {
      const listen = JSPFTrackToListen(playlistTrack);
      listens.push(listen);
    });
  }

  const dispatch = useBrainzPlayerDispatch();
  React.useEffect(() => {
    dispatch({ type: "SET_AMBIENT_QUEUE", data: listens });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listens]);

  return (
    <YearInMusic
      user={user ?? fallbackUser}
      yearInMusicData={yearInMusicData}
      topDiscoveriesPlaylist={topDiscoveriesPlaylist}
      topMissedRecordingsPlaylist={topMissedRecordingsPlaylist}
      missingSomePlaylistData={missingSomePlaylistData}
      hasNoPlaylists={hasNoPlaylists}
    />
  );
}
