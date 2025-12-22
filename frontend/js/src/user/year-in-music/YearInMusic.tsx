import * as React from "react";

import { toast } from "react-toastify";
import { isEmpty, isNil, isUndefined, last } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy, faShareAlt } from "@fortawesome/free-solid-svg-icons";
import { Link, useLocation, useNavigate, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { useSetAtom } from "jotai";
import { getYear } from "date-fns";
import { Helmet } from "react-helmet";
import tinycolor from "tinycolor2";
import GlobalAppContext from "../../utils/GlobalAppContext";

import ImageShareButtons from "./components/ImageShareButtons";
import { JSPFTrackToListen } from "../../playlists/utils";
import { ToastMsg } from "../../notifications/Notifications";
import FollowButton from "../components/follow/FollowButton";
import SEO, { YIMYearMetaTags } from "./SEO";
import { RouteQuery } from "../../utils/Loader";
import { setAmbientQueueAtom } from "../../common/brainzplayer/BrainzPlayerAtoms";
import TopLevelPlaylist, { getPlaylistByName } from "./components/YIMPlaylists";
import YIMMostListenedYear from "./components/YIMMostListenedYear";
import YIMArtistMap, { YIMArtistMapData } from "./components/YIMArtistMap";
import YIMGenreGraph, { GenreGraphDataT } from "./components/YIMGenreGraph";
import YIMNewReleases, {
  YIMNewReleasesData,
} from "./components/YIMNewReleases";
import YIMListeningActivity, {
  YIMListeningActivityData,
} from "./components/YIMListeningActivity";
import YIMStats from "./components/YIMStats";
import YIMCharts from "./components/YIMCharts";
import YIMFriends from "./components/YIMFriends";
import AlbumsCoverflow from "./components/AlbumsCoverflow";
import YIMSimilarUsers from "./components/YIMSimilarUsers";
import { COLOR_LB_BLUE } from "../../utils/constants";
import Preview from "../../explore/art-creator/components/Preview";
import Loader from "../../components/Loader";
import YIMYearSelection from "./components/YIMYearSelection";

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
    top_release_groups: UserReleaseGroupsResponse["payload"]["release_groups"];
    top_recordings: UserRecordingsResponse["payload"]["recordings"];
    similar_users: { [key: string]: number };
    listens_per_day: YIMListeningActivityData;
    most_listened_year: { [key: string]: number };
    total_listen_count: number;
    total_artists_count: number;
    total_listening_time: number;
    total_new_artists_discovered: number;
    total_recordings_count: number;
    total_release_groups_count: number;
    new_releases_of_top_artists: YIMNewReleasesData;
    artist_map: YIMArtistMapData;
  };
  topDiscoveriesPlaylist: JSPFPlaylist | undefined;
  topMissedRecordingsPlaylist: JSPFPlaylist | undefined;
  missingPlaylistData: boolean;
  genreGraphData: GenreGraphDataT;
};

type YearInMusicLoaderData = {
  user: YearInMusicProps["user"];
  data: YearInMusicProps["yearInMusicData"];
  genreGraphData: YearInMusicProps["genreGraphData"];
};

const colorSequence = [
  "#307750",
  "#A16551",
  "#693544",
  "#447D87",
  "#B2744D",
  "#4D326D",
  "#678838",
  "#C0B55D",
  "#3C4679",
  "#8C4D4D",
  "#8C4D89",
  "#EDCE69",
];

export const getYearColors = (year: number) => {
  const index = (year - 2003) % colorSequence.length;

  return [
    colorSequence[index],
    colorSequence[(index + 1) % colorSequence.length],
  ];
};
export const availableYears = [2021, 2022, 2023, 2024, 2025] as const;

export default function YearInMusic() {
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const location = useLocation();
  const params = useParams();
  const { year: yearParam = getYear(Date.now()), userName } = params;
  const year = Number(yearParam) as typeof availableYears[number];

  const { data, isLoading } = useQuery<YearInMusicLoaderData>(
    RouteQuery([`year-in-music`, params], location.pathname)
  );
  const fallbackUser = { name: userName ?? "" };
  const {
    user = fallbackUser,
    data: yearInMusicData,
    genreGraphData = {
      children: [],
      name: "",
    },
  } = data || {};

  /* Playlists */
  let missingPlaylistData = false;
  const topDiscoveriesPlaylist = getPlaylistByName(
    yearInMusicData,
    "playlist-top-discoveries-for-year",
    `Highlights songs that ${user.name} first listened to (more than once) in ${year}`
  );
  const topMissedRecordingsPlaylist = getPlaylistByName(
    yearInMusicData,
    "playlist-top-missed-recordings-for-year",
    `Favorite songs of ${user.name}'s most similar users that ${user.name} hasn't listened to this year`
  );
  if (!topDiscoveriesPlaylist || !topMissedRecordingsPlaylist) {
    missingPlaylistData = true;
  }

  const listens = React.useMemo(() => {
    const result: BaseListenFormat[] = [];

    if (yearInMusicData?.top_recordings) {
      yearInMusicData.top_recordings.forEach((recording) => {
        result.push({
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
        });
      });
    }

    if (topDiscoveriesPlaylist) {
      topDiscoveriesPlaylist.track.slice(0, 5).forEach((playlistTrack) => {
        result.push(JSPFTrackToListen(playlistTrack));
      });
    }

    if (topMissedRecordingsPlaylist) {
      topMissedRecordingsPlaylist.track.slice(0, 5).forEach((playlistTrack) => {
        result.push(JSPFTrackToListen(playlistTrack));
      });
    }

    return result;
  }, [
    yearInMusicData?.top_recordings,
    topDiscoveriesPlaylist,
    topMissedRecordingsPlaylist,
  ]);

  const setAmbientQueue = useSetAtom(setAmbientQueueAtom);
  // CHECK THAT WE ADD LISTENS FROM VARIOUS PARTS OF THE YIM DATA
  React.useEffect(() => {
    setAmbientQueue(listens);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listens]);

  const [followingList, setFollowingList] = React.useState<string[]>([]);
  const [
    followingListForLoggedInUser,
    setFollowingListForLoggedInUser,
  ] = React.useState<string[]>([]);

  const getFollowing = React.useCallback(async () => {
    if (!user?.name) {
      return;
    }
    try {
      const response = await APIService.getFollowingForUser(user.name);
      const { following } = response;
      setFollowingList(following);
    } catch (err) {
      toast.error(
        <ToastMsg
          title={`Error while fetching the users ${user.name} follows`}
          message={err.toString()}
        />,
        { toastId: "fetch-following-error" }
      );
    }
  }, [APIService, user?.name]);

  const getFollowingForLoggedInUser = React.useCallback(async () => {
    if (!currentUser?.name) {
      return;
    }
    try {
      const response = await APIService.getFollowingForUser(currentUser.name);
      const { following } = response;
      setFollowingListForLoggedInUser(following);
    } catch (err) {
      toast.error(
        <ToastMsg
          title="Error while fetching the users you follow"
          message={err.toString()}
        />,
        { toastId: "fetch-following-error" }
      );
    }
  }, [APIService, currentUser?.name]);

  React.useEffect(() => {
    getFollowingForLoggedInUser();
    // initial following for displayed user
    getFollowing();
    // keep these stable via deps
  }, [getFollowingForLoggedInUser, getFollowing]);

  const updateFollowingList = React.useCallback(
    (aUser: ListenBrainzUser, action: "follow" | "unfollow") => {
      const newFollowingList = [...followingListForLoggedInUser];
      const index = newFollowingList.findIndex(
        (following) => following === aUser.name
      );
      if (action === "follow" && index === -1) {
        newFollowingList.push(aUser.name);
      }
      if (action === "unfollow" && index !== -1) {
        newFollowingList.splice(index, 1);
      }
      setFollowingListForLoggedInUser(newFollowingList);
    },
    [followingListForLoggedInUser]
  );

  const loggedInUserFollowsUser = (aUser: ListenBrainzUser): boolean => {
    if (isNil(currentUser) || isEmpty(currentUser)) {
      return false;
    }
    return followingListForLoggedInUser.includes(aUser.name);
  };

  const sharePage = () => {
    const dataToShare: ShareData = {
      title: `My ${year} in music`,
      url: window.location.toString(),
    };
    if (navigator.canShare && navigator.canShare(dataToShare)) {
      navigator.share(dataToShare).catch((error) => {
        toast.error(
          <ToastMsg title="Error sharing image" message={error.toString()} />,
          { toastId: "sharing-image-error" }
        );
      });
    }
  };

  const gradientColors = getYearColors(Number(year));
  const accentColor = COLOR_LB_BLUE;
  const textColor = "#F1F2E1";
  const cardBackgroundColor = textColor;
  // const backgroundGradient = `linear-gradient(to right, ${gradientColors.join(
  //   ", "
  // )})`;
  const svgStyles = `
        text > tspan,
        .accent-color {
          fill: ${textColor};
        }
        .accent-color-stroke {
          stroke: ${textColor};
        }
        stop:first-child {
          stop-color: ${gradientColors[0]};
          }
        .bg-color-1 {
          fill: ${gradientColors[0]};
        }
        stop:nth-child(2) {
          stop-color: ${last(gradientColors)};
        }
        .bg-color-2 {
          fill: ${last(gradientColors)};
        }
  `;

  const missingSomeData = React.useMemo(() => {
    let missing = missingPlaylistData;
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
      missing = true;
    }
    return missing;
  }, [yearInMusicData, missingPlaylistData]);

  const hasSomeData = !!yearInMusicData && !isEmpty(yearInMusicData);

  const isUserLoggedIn = !isNil(currentUser) && !isEmpty(currentUser);
  const isCurrentUser = user.name === currentUser?.name;
  const yourOrUsersName = isCurrentUser ? "your" : `${user.name}'s`;
  const encodedUsername = encodeURIComponent(user.name);

  /* Most listened years */

  const linkToUserProfile = `https://listenbrainz.org/user/${encodedUsername}`;
  const linkToThisPage = `${linkToUserProfile}/year-in-music/${year}`;

  const userShareBar = (
    <div className="content-card">
      <div className="link-section">
        {isUserLoggedIn && user.name !== currentUser?.name && (
          <FollowButton
            type="icon-only btn-info"
            user={user}
            loggedInUserFollowsUser={loggedInUserFollowsUser(user)}
          />
        )}
        <Link
          to={`/user/${encodedUsername}/`}
          role="button"
          className="btn btn-info"
        >
          ListenBrainz Profile
        </Link>
        <div
          className="input-group"
          style={{ width: "auto", alignItems: "center" }}
        >
          <input
            type="text"
            className="form-control"
            size={linkToThisPage.length - 5}
            value={linkToThisPage}
            readOnly
          />
          <button
            type="button"
            className="btn btn-info"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(linkToThisPage);
                toast.success(
                  <ToastMsg
                    title="Link copied"
                    message="Link copied to clipboard"
                  />,
                  { toastId: "link-copied" }
                );
              } catch (err) {
                toast.error(
                  <ToastMsg title="Error copying link" message={String(err)} />,
                  { toastId: "copy-link-error" }
                );
              }
            }}
            aria-label="Copy link to clipboard"
          >
            <FontAwesomeIcon icon={faCopy} />
          </button>
        </div>
        {!isUndefined(navigator.canShare) && (
          <div className="btn btn-info">
            <FontAwesomeIcon icon={faShareAlt} onClick={sharePage} />
          </div>
        )}
      </div>
    </div>
  );

  const encodedBgColor1 = encodeURIComponent(gradientColors[0]);
  const encodedBgColor2 = encodeURIComponent(gradientColors[1]);
  const encodedAccentColor = encodeURIComponent(textColor);
  const overviewImageUrl = `${APIService.APIBaseURI}/art/year-in-music/${year}/${encodedUsername}?image=overview&bg-color-1=${encodedBgColor1}&bg-color-2=${encodedBgColor2}&accent-color=${encodedAccentColor}`;
  return (
    <div
      id="year-in-music"
      className={`yim-${year}`}
      style={{
        ["--cardBackgroundColor" as any]: cardBackgroundColor,
        ["--accentColor" as any]: tinycolor
          .mostReadable(cardBackgroundColor, gradientColors, {
            includeFallbackColors: false,
          })
          .darken(5)
          .saturate(5)
          .toHexString(),
        ["--gradientColor1" as any]: gradientColors[0],
        ["--gradientColor2" as any]: gradientColors[1],
      }}
    >
      <div>
        <SEO year={year} userName={user?.name} />
        <YIMYearMetaTags />
        <Helmet>
          <link
            rel="preload"
            href="/static/img/year-in-music/header.png"
            as="image"
          />
          <link rel="preload" href={overviewImageUrl} as="image" />
        </Helmet>
        <div id="main-header">
          <div className="user-name">{user.name}&apos;s</div>
          <div className="header-image">
            <img
              src="/static/img/year-in-music/header.png"
              alt="Year in Music"
              className="w-100"
              style={{ opacity: 0.2 }}
            />
            <img
              src="/static/img/year-in-music/header.png"
              alt="Year in Music"
              className="w-100"
              style={{ mixBlendMode: "overlay" }}
            />
          </div>
        </div>
        <Loader className="loader-container" isLoading={isLoading} />
        <YIMYearSelection
          year={year}
          encodedUsername={encodedUsername}
          yearInMusicData={yearInMusicData}
        />
        {!hasSomeData && (
          <div className="no-yim-message">
            <p className="center-p">Oh no!</p>
            <p className="center-p">
              We don&apos;t have enough {year} statistics for {user.name}.
            </p>
            <p className="center-p">
              <Link to="/settings/music-services/details/">Submit</Link> enough
              listens before the end of December to generate your #yearinmusic
              next year.
            </p>
          </div>
        )}
        <div role="main">
          {userShareBar}
          {hasSomeData && (
            <>
              {missingSomeData && (
                <div className="alert alert-warning">
                  Heads up: We were unable to compute all of the parts of Your
                  Year in Music due to not enough listens or an issue in our
                  database, but we&apos;re showing you everything that we were
                  able to make. Your page might look a bit different than
                  others.
                </div>
              )}
              <div className="section">
                <div className="content-card" id="overview">
                  <div className="bg-transparent card-bg center-p mt-5 p-0">
                    <Preview
                      className="img-fluid border-radius"
                      url={overviewImageUrl}
                      styles={{
                        textColor,
                        bgColor1: gradientColors[0],
                        bgColor2: last(gradientColors),
                      }}
                    />
                  </div>
                  <div className="yim-share-button-container">
                    <ImageShareButtons
                      svgURL={overviewImageUrl}
                      shareUrl={linkToThisPage}
                      shareText={`Check out my ListenBrainz stats for ${year}`}
                      shareTitle={`My year ${year} in music`}
                      fileName={`${user.name}-overview-${year}`}
                      customStyles={svgStyles}
                    />
                  </div>
                </div>
              </div>

              <div className="section">
                <div className="content-card" id="top-releases">
                  <h3 className="flex-center">Top albums of {year}</h3>
                  <AlbumsCoverflow
                    topReleaseGroups={yearInMusicData.top_release_groups}
                  />
                  <div className="yim-share-button-container">
                    <ImageShareButtons
                      svgURL={`${APIService.APIBaseURI}/art/year-in-music/${year}/${encodedUsername}?image=albums&bg-color-1=${encodedBgColor1}&bg-color-2=${encodedBgColor2}&accent-color=${encodedAccentColor}`}
                      shareUrl={`${linkToThisPage}#top-albums`}
                      shareText={`Check out my top albums for ${year} on ListenBrainz`}
                      shareTitle={`My top albums of ${year}`}
                      fileName={`${user.name}-top-albums-${year}`}
                      customStyles={svgStyles}
                    />
                  </div>
                </div>
              </div>

              <YIMCharts
                yearInMusicData={yearInMusicData}
                userName={user.name}
                year={year}
                customStyles={svgStyles}
                gradientColors={gradientColors}
                accentColor={accentColor}
              />

              <div className="section" id="stats">
                <div className="content-card">
                  <h3 className="flex-center">Your statistics for {year}</h3>
                  <YIMStats
                    yearInMusicData={yearInMusicData}
                    userName={user.name}
                  />
                  <YIMListeningActivity
                    listensPerDay={yearInMusicData.listens_per_day}
                    userName={user.name}
                    year={year}
                    gradientColors={gradientColors}
                  />
                  <YIMMostListenedYear
                    mostListenedYearData={yearInMusicData.most_listened_year}
                    userName={user.name}
                    gradientColors={gradientColors}
                  />
                  <YIMArtistMap
                    artistMapData={yearInMusicData.artist_map}
                    yourOrUsersName={yourOrUsersName}
                    gradientColors={gradientColors}
                  />
                  {genreGraphData && (
                    <YIMGenreGraph
                      genreGraphData={genreGraphData}
                      userName={user.name}
                      gradientColors={gradientColors}
                    />
                  )}
                  <div className="yim-share-button-container">
                    <ImageShareButtons
                      svgURL={`${APIService.APIBaseURI}/art/year-in-music/${year}/${encodedUsername}?image=stats&bg-color-1=${encodedBgColor1}&bg-color-2=${encodedBgColor2}&accent-color=${encodedAccentColor}`}
                      shareUrl={`${linkToThisPage}#stats`}
                      shareTitle={`My music listening in ${year} on ListenBrainz`}
                      fileName={`${user.name}-stats-${year}`}
                      customStyles={svgStyles}
                    />
                  </div>
                </div>
              </div>

              <div className="section">
                <div className="flex flex-wrap" id="playlists">
                  {topDiscoveriesPlaylist && (
                    <TopLevelPlaylist
                      year={year}
                      topLevelPlaylist={topDiscoveriesPlaylist}
                      coverArtKey="discovery-playlist"
                      userName={user.name}
                      customStyles={svgStyles}
                      gradientColors={gradientColors}
                      accentColor={accentColor}
                    />
                  )}
                  {topMissedRecordingsPlaylist && (
                    <TopLevelPlaylist
                      year={year}
                      topLevelPlaylist={topMissedRecordingsPlaylist}
                      coverArtKey="missed-playlist"
                      userName={user.name}
                      customStyles={svgStyles}
                      gradientColors={gradientColors}
                      accentColor={accentColor}
                    />
                  )}
                </div>
              </div>
              <div className="section">
                <div className="flex flex-wrap">
                  <YIMNewReleases
                    newReleases={yearInMusicData.new_releases_of_top_artists}
                    userName={user.name}
                    year={year}
                  />
                  <YIMSimilarUsers
                    similarUsers={yearInMusicData.similar_users}
                    updateFollowingList={updateFollowingList}
                    loggedInUserFollowsUser={loggedInUserFollowsUser}
                    userName={user.name}
                    year={year}
                  />
                </div>
              </div>
            </>
          )}
          {followingList.length > 0 && (
            <YIMFriends
              followingList={followingList}
              userName={user.name}
              year={year}
            />
          )}

          {/* ADD Community Year in Music tools ♡HERE */}

          <div className="section">
            {userShareBar}
            <div className="closing-remarks">
              <div
                className="overlay-image-container mb-5"
                style={{ width: "50px", height: "50px" }}
              >
                <img
                  src="/static/img/year-in-music/heart.png"
                  alt="With love,"
                />
                <img
                  src="/static/img/year-in-music/heart.png"
                  alt="With love,"
                />
              </div>
              <div
                className="overlay-image-container mb-5"
                style={{ maxWidth: "250px", height: "80px" }}
              >
                <img
                  src="/static/img/year-in-music/listenbrainz-footer.png"
                  alt="The ListenBrainz team"
                />
                <img
                  src="/static/img/year-in-music/listenbrainz-footer.png"
                  alt="The ListenBrainz team"
                />
              </div>
              <p className="mb-4 bold">
                Wishing you a very cozy {year + 1}, from the ListenBrainz team.
              </p>
              <p className="mb-5">
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
                  href="https://matrix.to/#/#metabrainz-all:chatbrainz.org"
                  rel="noopener noreferrer"
                >
                  Matrix
                </a>
                ,&nbsp;
                <a
                  target="_blank"
                  href="https://discord.gg/R4hBw972QA"
                  rel="noopener noreferrer"
                >
                  Discord
                </a>
                ,&nbsp;
                <a
                  target="_blank"
                  href="https://bsky.app/profile/listenbrainz.org"
                  rel="noopener noreferrer"
                >
                  Bluesky
                </a>
                &nbsp;or&nbsp;
                <a
                  target="_blank"
                  href="https://mastodon.social/@ListenBrainz"
                  rel="noopener noreferrer"
                >
                  Mastodon
                </a>
                .
              </p>
              <div
                className="overlay-image-container mt-5 mb-5"
                style={{ maxWidth: "200px", height: "85px" }}
              >
                <img
                  src="/static/img/year-in-music/OSS-footer.png"
                  alt="Open source and ethical forever"
                />
                <img
                  src="/static/img/year-in-music/OSS-footer.png"
                  alt="Open source and ethical forever"
                />
              </div>
            </div>
          </div>
        </div>
        {/* Trick to load the font files for use with the SVG render CHECK IF THIS IS STILL REQUIRED */}
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
    </div>
  );
}
