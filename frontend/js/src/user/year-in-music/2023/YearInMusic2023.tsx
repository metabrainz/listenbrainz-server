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
  faCircleChevronLeft,
  faCircleChevronRight,
  faCopy,
  faHeadphones,
  faQuestionCircle,
  faShareAlt,
} from "@fortawesome/free-solid-svg-icons";
import { LazyLoadImage } from "react-lazy-load-image-component";
import tinycolor from "tinycolor2";
import humanizeDuration from "humanize-duration";
import { Link, useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import GlobalAppContext from "../../../utils/GlobalAppContext";

import {
  generateAlbumArtThumbnailLink,
  getArtistLink,
  getStatsArtistLink,
} from "../../../utils/utils";
import { getEntityLink } from "../../stats/utils";
import ImageShareButtons from "./components/ImageShareButtons";

import ListenCard from "../../../common/listens/ListenCard";
import UserListModalEntry from "../../components/follow/UserListModalEntry";
import { JSPFTrackToListen } from "../../../playlists/utils";
import CustomChoropleth from "../../stats/components/Choropleth";
import { ToastMsg } from "../../../notifications/Notifications";
import FollowButton from "../../components/follow/FollowButton";
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
    top_genres: Array<{
      genre: string;
      genre_count: number;
      genre_count_percent: number;
    }>;
    top_release_groups: Array<{
      artists?: Array<MBIDMappingArtist>;
      artist_name: string;
      artist_mbids: string[];
      listen_count: number;
      release_group_name: string;
      release_group_mbid: string;
      caa_id?: number;
      caa_release_mbid?: string;
    }>;
    top_recordings: Array<{
      artists?: Array<MBIDMappingArtist>;
      artist_name: string;
      artist_mbids: string[];
      listen_count: number;
      release_name: string;
      release_mbid: string;
      track_name: string;
      recording_mbid: string;
      caa_id?: number;
      caa_release_mbid?: string;
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
    total_artists_count: number;
    total_listening_time: number;
    total_new_artists_discovered: number;
    total_recordings_count: number;
    total_release_groups_count: number;
    new_releases_of_top_artists: Array<{
      title: string;
      release_group_mbid: string;
      caa_id?: number;
      caa_release_mbid?: string;
      artist_credit_mbids: string[];
      artist_credit_name: string;
      artists?: Array<MBIDMappingArtist>;
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
  missingPlaylistData: boolean;
};

type YearInMusicLoaderData = {
  user: YearInMusicProps["user"];
  data: YearInMusicProps["yearInMusicData"];
};

enum YIM2023Color {
  green = "#4C6C52",
  red = "#BE4A55",
  blue = "#567276",
  brown = "#4C4442",
}
const YIM2023ColorStrings = Object.values(YIM2023Color);

const buddiesImages = [
  "/static/img/year-in-music-23/fish.png",
  "/static/img/year-in-music-23/dog.png",
  "/static/img/year-in-music-23/worm.png",
  "/static/img/year-in-music-23/cat.png",
  "/static/img/year-in-music-23/trunk.png",
  "/static/img/year-in-music-23/dog-tall.png",
  "/static/img/year-in-music-23/ghost-square.png",
];

export type YearInMusicState = {
  followingList: Array<string>;
  followingListForLoggedInUser: Array<string>;
  selectedMetric: "artist" | "listen";
  selectedColor: YIM2023Color;
};

export default class YearInMusic extends React.Component<
  YearInMusicProps,
  YearInMusicState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  private buddiesScrollContainer: React.RefObject<HTMLDivElement>;

  constructor(props: YearInMusicProps) {
    super(props);
    this.state = {
      followingList: [],
      followingListForLoggedInUser: [],
      selectedMetric: "listen",
      selectedColor: YIM2023Color.green,
    };
    this.buddiesScrollContainer = React.createRef();
  }

  async componentDidMount() {
    await this.getFollowing();
    await this.getFollowingForLoggedInUser();
  }

  async componentDidUpdate(prevProps: YearInMusicProps) {
    const { user } = this.props;
    if (user !== prevProps.user) {
      await this.getFollowing();
    }
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
    const { APIService } = this.context;
    const { user } = this.props;
    const { getFollowingForUser } = APIService;
    if (!user?.name) {
      return;
    }
    try {
      const response = await getFollowingForUser(user.name);
      const { following } = response;

      this.setState({ followingList: following });
    } catch (err) {
      toast.error(
        <ToastMsg
          title={`Error while fetching the users ${user.name} follows`}
          message={err.toString()}
        />,
        { toastId: "fetch-following-error" }
      );
    }
  };

  getFollowingForLoggedInUser = async () => {
    const { APIService, currentUser } = this.context;
    const { getFollowingForUser } = APIService;
    if (!currentUser?.name) {
      return;
    }
    try {
      const response = await getFollowingForUser(currentUser.name);
      const { following } = response;

      this.setState({ followingListForLoggedInUser: following });
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
    const { followingListForLoggedInUser } = this.state;
    const newFollowingList = [...followingListForLoggedInUser];
    const index = newFollowingList.findIndex(
      (following) => following === user.name
    );
    if (action === "follow" && index === -1) {
      newFollowingList.push(user.name);
    }
    if (action === "unfollow" && index !== -1) {
      newFollowingList.splice(index, 1);
    }
    this.setState({ followingListForLoggedInUser: newFollowingList });
  };

  loggedInUserFollowsUser = (user: ListenBrainzUser): boolean => {
    const { currentUser } = this.context;
    const { followingListForLoggedInUser } = this.state;

    if (isNil(currentUser) || isEmpty(currentUser)) {
      return false;
    }

    return followingListForLoggedInUser.includes(user.name);
  };

  sharePage = () => {
    const dataToShare: ShareData = {
      title: "My 2023 in music",
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
    coverArtKey: string,
    listens: Array<Listen>
  ): JSX.Element | undefined => {
    if (!topLevelPlaylist) {
      return undefined;
    }
    const { APIService } = this.context;
    const { selectedColor } = this.state;
    const { user } = this.props;
    return (
      <div className="card content-card mb-10" id={`${coverArtKey}`}>
        <div className="center-p heading">
          <object
            className="img-header"
            data={`${APIService.APIBaseURI}/art/year-in-music/2023/${user.name}?image=${coverArtKey}&branding=False`}
          >{`SVG of cover art for ${topLevelPlaylist.title}`}</object>
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
        <div className="yim-share-button-container">
          <ImageShareButtons
            svgURL={`${APIService.APIBaseURI}/art/year-in-music/2023/${user.name}?image=${coverArtKey}`}
            shareUrl={`https://listenbrainz.org/user/${user.name}/year-in-music/2023#top-albums`}
            // shareText="Check out my"
            shareTitle="My 2023 ListenBrainz playlists"
            fileName={`${user.name}-${coverArtKey}-2023`}
            customStyles={`.background {\nfill: ${selectedColor};\n}\n`}
          />
        </div>
      </div>
    );
  };

  selectColor = (event: React.MouseEvent | React.KeyboardEvent) => {
    const color = (event.currentTarget.getAttribute(
      "data-color"
    ) as unknown) as YIM2023Color;
    this.setState({ selectedColor: color });
  };

  manualScroll: React.ReactEventHandler<HTMLElement> = (event) => {
    if (!this.buddiesScrollContainer?.current) {
      return;
    }
    if (event?.currentTarget.classList.contains("forward")) {
      this.buddiesScrollContainer.current.scrollBy({
        left: 330,
        top: 0,
        behavior: "smooth",
      });
    } else {
      this.buddiesScrollContainer.current.scrollBy({
        left: -330,
        top: 0,
        behavior: "smooth",
      });
    }
  };

  render() {
    const {
      user,
      yearInMusicData,
      topDiscoveriesPlaylist,
      topMissedRecordingsPlaylist,
      missingPlaylistData,
    } = this.props;
    const { selectedMetric, selectedColor, followingList } = this.state;
    const { APIService, currentUser } = this.context;
    const listens: BaseListenFormat[] = [];

    // Some data might not have been calculated for some users
    // This boolean lets us warn them of that
    let missingSomeData = missingPlaylistData;
    const hasSomeData = !!yearInMusicData && !isEmpty(yearInMusicData);
    if (
      !yearInMusicData ||
      !yearInMusicData.top_release_groups ||
      !yearInMusicData.top_recordings ||
      !yearInMusicData.top_artists ||
      !yearInMusicData.top_genres ||
      !yearInMusicData.listens_per_day ||
      !yearInMusicData.total_listen_count ||
      !yearInMusicData.total_listening_time ||
      !yearInMusicData.total_new_artists_discovered ||
      !yearInMusicData.total_recordings_count ||
      !yearInMusicData.total_release_groups_count ||
      !yearInMusicData.day_of_week ||
      !yearInMusicData.new_releases_of_top_artists ||
      !yearInMusicData.artist_map ||
      !yearInMusicData.total_artists_count ||
      !yearInMusicData.similar_users ||
      isEmpty(yearInMusicData.most_listened_year)
    ) {
      missingSomeData = true;
    }

    const isUserLoggedIn = !isNil(currentUser) && !isEmpty(currentUser);
    // Is the logged-in user looking at their own page?
    const isCurrentUser = user.name === currentUser?.name;
    const youOrUsername = isCurrentUser ? "you" : `${user.name}`;
    const yourOrUsersName = isCurrentUser ? "your" : `${user.name}'s`;

    /* Most listened years */
    let mostListenedYearDataForGraph;
    let mostListenedYearTicks;
    if (yearInMusicData && !isEmpty(yearInMusicData?.most_listened_year)) {
      const mostListenedYears = Object.keys(yearInMusicData.most_listened_year);
      // Ensure there are no holes between years
      const filledYears = range(
        Number(mostListenedYears[0]),
        Number(mostListenedYears[mostListenedYears.length - 1]) + 1
      );
      mostListenedYearDataForGraph = filledYears.map((year: number) => ({
        year,
        // Set to 0 for years without data
        songs: String(yearInMusicData?.most_listened_year[String(year)] ?? 0),
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
    if (!isEmpty(yearInMusicData?.artist_map)) {
      artistMapDataForGraph = yearInMusicData?.artist_map.map((country) => ({
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
    if (!isEmpty(yearInMusicData?.similar_users)) {
      sortedSimilarUsers = toPairs(yearInMusicData?.similar_users).sort(
        (a, b) => b[1] - a[1]
      );
    }

    /* Listening history calendar graph */
    let listensPerDayForGraph;
    if (!isEmpty(yearInMusicData?.listens_per_day)) {
      listensPerDayForGraph = yearInMusicData?.listens_per_day
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

    const linkToUserProfile = `https://listenbrainz.org/user/${user.name}`;
    const linkToThisPage = `${linkToUserProfile}/year-in-music/2023`;
    const imageShareCustomStyles = `.background {\nfill: ${selectedColor};\n}\n`;
    const statsImageCustomStyles = `.background, text {\nfill: ${selectedColor};\n}\n.outline {\nstroke: ${selectedColor};\n}\n`;

    let newArtistsDiscovered: number | string =
      yearInMusicData?.total_new_artists_discovered ?? 0;
    let newArtistsDiscoveredPercentage;
    if (yearInMusicData) {
      newArtistsDiscoveredPercentage = Math.round(
        (yearInMusicData.total_new_artists_discovered /
          yearInMusicData.total_artists_count) *
          100
      );
    }
    if (!Number.isNaN(newArtistsDiscoveredPercentage)) {
      newArtistsDiscovered = `${newArtistsDiscoveredPercentage}%`;
    }
    const userShareBar = (
      <div className="card content-card">
        <div className="link-section">
          {isUserLoggedIn && (
            <FollowButton
              type="icon-only btn-info"
              user={user}
              loggedInUserFollowsUser={this.loggedInUserFollowsUser(user)}
            />
          )}
          <Link
            to={`/user/${user.name}/`}
            role="button"
            className="btn btn-info"
          >
            ListenBrainz Profile
          </Link>
          <div className="input-group">
            <input
              type="text"
              className="form-control"
              size={linkToThisPage.length - 5}
              value={linkToThisPage}
            />
            <span className="btn btn-info input-group-addon">
              <FontAwesomeIcon
                icon={faCopy}
                onClick={async () => {
                  await navigator.clipboard.writeText(linkToThisPage);
                }}
              />
            </span>
          </div>
          {!isUndefined(navigator.canShare) && (
            <div className="btn btn-info">
              <FontAwesomeIcon icon={faShareAlt} onClick={this.sharePage} />
            </div>
          )}
        </div>
      </div>
    );
    return (
      <div
        id="year-in-music"
        className="yim-2023"
        role="main"
        style={{ ["--selectedColor" as any]: selectedColor }}
      >
        <SEO year={2023} userName={user?.name} />
        <YIMYearMetaTags year={2023} />
        <div id="main-header">
          <div className="color-picker">
            <img
              className="pick-color-caption"
              src="/static/img/year-in-music-23/pick-color.png"
              alt="Pick a color"
            />
            {YIM2023ColorStrings.map((color) => {
              return (
                <div
                  aria-label={`Select color ${color}`}
                  role="button"
                  tabIndex={0}
                  className="color-selector"
                  style={{ backgroundColor: color }}
                  onClick={this.selectColor}
                  onKeyDown={this.selectColor}
                  data-color={color}
                />
              );
            })}
          </div>
          <div className="hashtag">#YearInMusic</div>
          {hasSomeData ? (
            <span
              className="masked-image"
              style={{
                WebkitMaskImage:
                  "url('/static/img/year-in-music-23/yim23-logo.png')",
              }}
            >
              <img
                className="img-responsive header-image"
                src="/static/img/year-in-music-23/yim23-logo.png"
                alt="Your year in music 2023"
              />
            </span>
          ) : (
            <>
              <span
                className="masked-image"
                style={{
                  WebkitMaskImage:
                    "url('/static/img/year-in-music-23/flower.png')",
                  marginTop: "6vh",
                }}
              >
                <img
                  src="/static/img/year-in-music-23/flower.png"
                  alt="Your year in music 2023"
                />
              </span>
              <div className="no-yim-message">
                <p className="center-p">Oh no!</p>
                <p className="center-p">
                  We don&apos;t have enough 2023 statistics for {user.name}.
                </p>
                <p className="center-p">
                  <Link to="/settings/music-services/details/">Submit</Link>{" "}
                  enough listens before the end of December to generate your
                  #yearinmusic next year.
                </p>
              </div>
            </>
          )}
          <div className="user-name">{user.name}</div>
          <div className="arrow-down" />
        </div>

        {userShareBar}
        {hasSomeData && (
          <>
            {missingSomeData && (
              <div className="alert alert-warning">
                Heads up: We were unable to compute all of the parts of Your
                Year in Music due to not enough listens or an issue in our
                database, but we&apos;re showing you everything that we were
                able to make. Your page might look a bit different than others.
              </div>
            )}
            <div className="section">
              <div className="card content-card" id="overview">
                <h3 className="flex-center">Overview</h3>
                <div className="center-p">
                  <object
                    className="card"
                    data={`${APIService.APIBaseURI}/art/year-in-music/2023/${user.name}?image=overview`}
                  >
                    Overview
                  </object>
                </div>
                <div className="yim-share-button-container">
                  <ImageShareButtons
                    svgURL={`${APIService.APIBaseURI}/art/year-in-music/2023/${user.name}?image=overview`}
                    shareUrl={linkToThisPage}
                    shareText="Check out my ListenBrainz stats for 2023"
                    shareTitle="My year in music"
                    fileName={`${user.name}-overview-2023`}
                  />
                </div>
              </div>
            </div>

            {yearInMusicData.top_release_groups && (
              <div className="section">
                <div className="card content-card" id="top-releases">
                  <h3 className="flex-center">Top albums of 2023</h3>
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
                      {yearInMusicData.top_release_groups
                        .slice(0, 50)
                        .map((release_group) => {
                          if (
                            !release_group.caa_id ||
                            !release_group.caa_release_mbid
                          ) {
                            return null;
                          }
                          const coverArt = generateAlbumArtThumbnailLink(
                            release_group.caa_id,
                            release_group.caa_release_mbid,
                            500
                          );
                          return (
                            <SwiperSlide
                              key={`coverflow-${release_group.release_group_name}`}
                            >
                              <img
                                data-src={
                                  coverArt ??
                                  "/static/img/cover-art-placeholder.jpg"
                                }
                                alt={release_group.release_group_name}
                                className="swiper-lazy"
                              />
                              <div className="swiper-lazy-preloader swiper-lazy-preloader-white" />
                              <div title={release_group.release_group_name}>
                                {getEntityLink(
                                  "release-group",
                                  release_group.release_group_name,
                                  release_group.release_group_mbid
                                )}
                                <div className="small text-muted">
                                  {getStatsArtistLink(
                                    release_group.artists,
                                    release_group.artist_name,
                                    release_group.artist_mbids
                                  )}
                                </div>
                              </div>
                            </SwiperSlide>
                          );
                        })}
                    </Swiper>
                  </div>
                  <div className="yim-share-button-container">
                    <ImageShareButtons
                      svgURL={`${APIService.APIBaseURI}/art/year-in-music/2023/${user.name}?image=albums`}
                      shareUrl={`${linkToThisPage}#top-albums`}
                      // shareText="Check out my"
                      shareTitle="My top albums of 2023"
                      fileName={`${user.name}-top-albums-2023`}
                      customStyles={imageShareCustomStyles}
                    />
                  </div>
                </div>
              </div>
            )}

            <div className="section">
              <div className="header">
                Charts
                <div className="subheader">
                  {youOrUsername} {isCurrentUser ? "have" : "has"} great taste
                </div>
              </div>
              <div className="flex flex-wrap" style={{ gap: "2em" }}>
                {yearInMusicData.top_recordings && (
                  <div className="card content-card" id="top-tracks">
                    <div className="heading">
                      <img
                        className="img-header"
                        src="/static/img/year-in-music-23/peep-square.png"
                        alt="Top songs of 2023"
                      />
                      <h4>Top songs of 2023</h4>
                    </div>
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
                              mbid_mapping: {
                                recording_mbid: recording.recording_mbid,
                                release_mbid: recording.release_mbid,
                                artist_mbids: recording.artist_mbids,
                                artists: recording.artists,
                                caa_id: recording.caa_id,
                                caa_release_mbid: recording.caa_release_mbid,
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
                            />
                          );
                        })}
                    </div>
                    <div className="yim-share-button-container">
                      <ImageShareButtons
                        svgURL={`${APIService.APIBaseURI}/art/year-in-music/2023/${user.name}?image=tracks`}
                        shareUrl={`${linkToThisPage}#top-tracks`}
                        // shareText="Check out my"
                        shareTitle="My top tracks of 2023"
                        fileName={`${user.name}-top-tracks-2023`}
                        customStyles={imageShareCustomStyles}
                      />
                    </div>
                  </div>
                )}
                {yearInMusicData.top_artists && (
                  <div className="card content-card" id="top-artists">
                    <div className="heading">
                      <img
                        className="img-header"
                        src="/static/img/year-in-music-23/heart-square.png"
                        alt="Top artists of 2023"
                      />
                      <h4>Top artists of 2023</h4>
                    </div>
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
                          listens.push(listenHere);
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
                    <div className="yim-share-button-container">
                      <ImageShareButtons
                        svgURL={`${APIService.APIBaseURI}/art/year-in-music/2023/${user.name}?image=artists`}
                        shareUrl={`${linkToThisPage}#top-artists`}
                        // shareText="Check out my"
                        shareTitle="My top artists of 2023"
                        fileName={`${user.name}-top-artists-2023`}
                        customStyles={imageShareCustomStyles}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="section" id="stats">
              <div className="header">
                Statistics
                <div className="subheader">you are a wonderful human being</div>
              </div>
              <div className="card content-card">
                <div className="small-stats">
                  {yearInMusicData.total_listen_count && (
                    <div className="small-stat text-center">
                      <div className="value">
                        {yearInMusicData.total_listen_count}
                      </div>
                      <span>songs graced {yourOrUsersName} ears</span>
                    </div>
                  )}
                  {yearInMusicData.total_listening_time && (
                    <div className="small-stat text-center">
                      <div className="value">
                        {humanizeDuration(
                          yearInMusicData.total_listening_time * 1000,
                          {
                            largest: 1,
                            round: true,
                          }
                        )}
                      </div>
                      <span>of music (at least!)</span>
                    </div>
                  )}
                  {yearInMusicData.total_release_groups_count && (
                    <div className="small-stat text-center">
                      <div className="value">
                        {yearInMusicData.total_release_groups_count}
                      </div>
                      <span>albums in total</span>
                    </div>
                  )}
                  {yearInMusicData.total_artists_count && (
                    <div className="small-stat text-center">
                      <div className="value">
                        {yearInMusicData.total_artists_count}
                      </div>
                      <span>artists got {yourOrUsersName} attention</span>
                    </div>
                  )}
                  {newArtistsDiscovered && (
                    <div className="small-stat text-center">
                      <div className="value">{newArtistsDiscovered}</div>
                      <span>new artists discovered</span>
                    </div>
                  )}
                  {yearInMusicData.day_of_week && (
                    <div className="small-stat text-center">
                      <div className="value">{yearInMusicData.day_of_week}</div>
                      <span>was {yourOrUsersName} music day</span>
                    </div>
                  )}
                </div>
                {listensPerDayForGraph && (
                  <div className="" id="calendar">
                    <h3 className="text-center">
                      {capitalize(yourOrUsersName)} listening activity{" "}
                      <FontAwesomeIcon
                        icon={faQuestionCircle}
                        data-tip
                        data-for="listening-activity"
                        size="xs"
                      />
                      <Tooltip id="listening-activity">
                        How many tracks did {youOrUsername} listen to each day
                        of the year?
                      </Tooltip>
                    </h3>

                    <div className="graph-container">
                      <div className="graph">
                        <ResponsiveCalendar
                          from="2023-01-01"
                          to="2023-12-31"
                          data={listensPerDayForGraph as CalendarDatum[]}
                          emptyColor="#eeeeee"
                          colors={[
                            ...[1, 2, 3]
                              .map((multiplier) =>
                                tinycolor(selectedColor)
                                  .lighten(15 * multiplier)
                                  .toHexString()
                              )
                              .reverse(),
                            selectedColor,
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
                  </div>
                )}
                {mostListenedYearDataForGraph && (
                  <div className="" id="most-listened-year">
                    <h3 className="text-center">
                      What year are {yourOrUsersName} favorite songs from?{" "}
                      <FontAwesomeIcon
                        icon={faQuestionCircle}
                        data-tip
                        data-for="most-listened-year-helptext"
                        size="xs"
                      />
                      <Tooltip id="most-listened-year-helptext">
                        How much{" "}
                        {isCurrentUser ? "were you" : `was ${user.name}`} on the
                        lookout for new music this year? Not that we&apos;re
                        judging
                      </Tooltip>
                    </h3>
                    <div className="graph-container">
                      <div className="graph">
                        <ResponsiveBar
                          margin={{ left: 50, bottom: 45, right: 30, top: 30 }}
                          data={mostListenedYearDataForGraph}
                          padding={0.1}
                          layout="vertical"
                          keys={["songs"]}
                          indexBy="year"
                          colors={selectedColor}
                          enableLabel={false}
                          axisBottom={{
                            tickValues: mostListenedYearTicks,
                            tickRotation: -30,
                          }}
                          axisLeft={{
                            legend: "Number of listens",
                            legendOffset: -40,
                            legendPosition: "middle",
                          }}
                        />
                      </div>
                    </div>
                  </div>
                )}
                {artistMapDataForGraph && (
                  <div
                    className=""
                    id="user-artist-map"
                    style={{ marginTop: "1.5em" }}
                  >
                    <h3 className="text-center">
                      What countries are {yourOrUsersName} favorite artists
                      from?{" "}
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
                                  selectedMetric === "listen"
                                    ? "active"
                                    : undefined
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
                                  selectedMetric === "artist"
                                    ? "active"
                                    : undefined
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
                            ...[1, 2, 3]
                              .map((index) =>
                                tinycolor(selectedColor)
                                  .lighten(15 * index)
                                  .toHexString()
                              )
                              .reverse(),
                            selectedColor,
                            ...[1, 2].map((index) =>
                              tinycolor(selectedColor)
                                .darken(15 * index)
                                .toHexString()
                            ),
                          ]}
                        />
                      </div>
                    </div>
                  </div>
                )}
                <div className="yim-share-button-container">
                  <ImageShareButtons
                    svgURL={`${APIService.APIBaseURI}/art/year-in-music/2023/${user.name}?image=stats`}
                    shareUrl={`${linkToThisPage}#stats`}
                    shareTitle="My music listening in 2023"
                    fileName={`${user.name}-stats-2023`}
                    customStyles={statsImageCustomStyles}
                  />
                </div>
              </div>
            </div>
            {(Boolean(topDiscoveriesPlaylist) ||
              Boolean(topMissedRecordingsPlaylist)) && (
              <div className="section">
                <div className="header">
                  2023 Playlists
                  <div className="subheader">
                    {youOrUsername} {isCurrentUser ? "have" : "has"} earned
                    these
                  </div>
                </div>
                <div className="row flex flex-wrap" id="playlists">
                  {Boolean(topDiscoveriesPlaylist) &&
                    this.showTopLevelPlaylist(
                      0,
                      topDiscoveriesPlaylist,
                      "discovery-playlist",
                      listens
                    )}
                  {Boolean(topMissedRecordingsPlaylist) &&
                    this.showTopLevelPlaylist(
                      1,
                      topMissedRecordingsPlaylist,
                      "missed-playlist",
                      listens
                    )}
                </div>
              </div>
            )}
            <div className="section">
              <div className="header">
                Discover
                <div className="subheader">
                  there&apos;s a whole world out there
                </div>
              </div>
              <div className="flex flex-wrap">
                {yearInMusicData.new_releases_of_top_artists && (
                  <div
                    className="card content-card"
                    id="new-releases"
                    style={{ marginBottom: "2.5em" }}
                  >
                    <div className="heading">
                      <img
                        className="img-header"
                        src="/static/img/year-in-music-23/ghost-square.png"
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
                          Albums and singles released in 2023 from artists{" "}
                          {youOrUsername} listened to.
                          <br />
                          Missed anything?
                        </Tooltip>
                      </h4>
                    </div>
                    <div className="scrollable-area">
                      {yearInMusicData.new_releases_of_top_artists.map(
                        (release) => {
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
                                artist_mbids: release.artist_credit_mbids,
                                release_group_mbid: release.release_group_mbid,
                                release_group_name: release.title,
                                caa_id: release.caa_id,
                                caa_release_mbid: release.caa_release_mbid,
                                artists: release.artists,
                              },
                            },
                          };
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
                                {getArtistLink(listenHere)}
                              </span>
                            </>
                          );
                          listens.push(listenHere);
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
                      )}
                    </div>
                  </div>
                )}
                {sortedSimilarUsers && sortedSimilarUsers.length && (
                  <div
                    className="card content-card"
                    id="similar-users"
                    style={{ marginBottom: "2.5em" }}
                  >
                    <div className="heading">
                      <img
                        className="img-header"
                        src="/static/img/year-in-music-23/buddies-square.png"
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
                      {sortedSimilarUsers.map((userFromList) => {
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
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
        {Boolean(followingList.length) && (
          <div className="section">
            <div className="header">
              Friends
              <div className="subheader">visit {yourOrUsersName} buds</div>
            </div>
            <div id="buddies">
              <button
                className="btn-icon btn-transparent backward"
                type="button"
                onClick={this.manualScroll}
              >
                <FontAwesomeIcon icon={faCircleChevronLeft} />
              </button>
              <div
                className="flex card-container dragscroll"
                ref={this.buddiesScrollContainer}
              >
                {followingList.slice(0, 15).map((followedUser, index) => {
                  return (
                    <Link
                      className="buddy content-card card"
                      to={`/user/${followedUser}/year-in-music/2023/`}
                    >
                      <div className="img-container">
                        <img
                          src={buddiesImages[index % 7]}
                          alt="Music buddies"
                        />
                      </div>
                      <div className="small-stat">
                        <div className="value">{followedUser}</div>
                      </div>
                    </Link>
                  );
                })}
              </div>
              <button
                className="btn-icon btn-transparent forward"
                type="button"
                onClick={this.manualScroll}
              >
                <FontAwesomeIcon icon={faCircleChevronRight} />
              </button>
            </div>
          </div>
        )}
        <div className="cover-art-composite">
          <div className="section">
            <div className="header">
              2023 Releases
              <div className="subheader">
                just some of the great music that came out in 2023.
                <br />
                drag, scroll and click to listen to albums
              </div>
            </div>
          </div>
          <div className="composite-image">
            <Link to="/explore/cover-art-collage/2023/">
              <LazyLoadImage
                src="https://staticbrainz.org/LB/year-in-music/2023/mosaic-2023-small.jpg"
                placeholderSrc="https://staticbrainz.org/LB/year-in-music/2023/mosaic-2023-small.jpg"
                srcSet="https://staticbrainz.org/LB/year-in-music/2023/mosaic-2023-small.jpg 500w,
                https://staticbrainz.org/LB/year-in-music/2023/mosaic-2023-medium.jpg 1000w,
                https://staticbrainz.org/LB/year-in-music/2023/mosaic-2023-large.jpg 2000w"
                sizes="(max-width:992px) 100vw, calc(100vw - 200px)"
                alt="2023 albums"
                loading="lazy"
                decoding="async"
              />
            </Link>
          </div>

          <div className="section">
            {userShareBar}
            <div className="closing-remarks">
              <span className="bold">
                Wishing you a restful 2024, from the ListenBrainz team.
              </span>
              <br />
              If you have questions or feedback don&apos;t hesitate to contact
              us
              <br />
              on&nbsp;
              <a
                target="_blank"
                href="https://community.metabrainz.org/c/listenbrainz/18"
                rel="noopener noreferrer"
              >
                our forums
              </a>
              ,&nbsp;
              <a
                target="_blank"
                href="mailto:listenbrainz@metabrainz.org"
                rel="noopener noreferrer"
              >
                by email
              </a>
              ,&nbsp;
              <a
                target="_blank"
                href="https://web.libera.chat/#metabrainz"
                rel="noopener noreferrer"
              >
                IRC
              </a>
              ,&nbsp;
              <a
                target="_blank"
                href="https://twitter.com/listenbrainz"
                rel="noopener noreferrer"
              >
                X
              </a>
              ,&nbsp;
              <a
                target="_blank"
                href="https://bsky.app/profile/metabrainz.bsky.social"
                rel="noopener noreferrer"
              >
                Bluesky
              </a>
              &nbsp;or&nbsp;
              <a
                target="_blank"
                href="https://mastodon.social/@metabrainz"
                rel="noopener noreferrer"
              >
                Mastodon
              </a>
              .
              <br />
              <br />
              Feeling nostalgic? See your previous Year in Music:{" "}
              <Link to={`/user/${user.name}/year-in-music/2022/`}>2022</Link>
            </div>
          </div>
        </div>
        {/* Trick to load the font files for use with the SVG render */}
        <span
          style={{
            fontFamily: "Inter, sans-serif",
            opacity: 0,
            position: "fixed",
          }}
        >
          x
        </span>
      </div>
    );
  }
}

export function YearInMusicWrapper() {
  const location = useLocation();
  const params = useParams();
  const { data } = useQuery<YearInMusicLoaderData>(
    RouteQuery(["year-in-music-2023", params], location.pathname)
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
    try {
      const playlist = get(yearInMusicData, playlistName);
      if (!playlist) {
        return undefined;
      }
      // Append manual description used in this page (rather than parsing HTML, ellipsis issues, etc.)
      if (description) {
        playlist.annotation = description;
      }
      return playlist;
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error(`"Error parsing ${playlistName}:`, error);
      return undefined;
    }
  }

  /* Playlists */
  let missingPlaylistData = false;
  const topDiscoveriesPlaylist = getPlaylistByName(
    "playlist-top-discoveries-for-year",
    `Highlights songs that ${user.name} first listened to (more than once) in 2023`
  );
  const topMissedRecordingsPlaylist = getPlaylistByName(
    "playlist-top-missed-recordings-for-year",
    `Favorite songs of ${user.name}'s most similar users that ${user.name} hasn't listened to this year`
  );
  if (!topDiscoveriesPlaylist || !topMissedRecordingsPlaylist) {
    missingPlaylistData = true;
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
      missingPlaylistData={missingPlaylistData}
    />
  );
}
