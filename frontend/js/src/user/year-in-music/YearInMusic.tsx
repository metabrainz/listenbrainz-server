import * as React from "react";

import { toast } from "react-toastify";
import { isEmpty, isNil, isUndefined } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy, faShareAlt } from "@fortawesome/free-solid-svg-icons";
import { Link, useLocation, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { useSetAtom } from "jotai";
import { getYear } from "date-fns";
import GlobalAppContext from "../../utils/GlobalAppContext";

import ImageShareButtons from "./components/ImageShareButtons";
import { JSPFTrackToListen } from "../../playlists/utils";
import { ToastMsg } from "../../notifications/Notifications";
import FollowButton from "../components/follow/FollowButton";
import SEO, { YIMYearMetaTags } from "./SEO";
import { RouteQuery } from "../../utils/Loader";
import { setAmbientQueueAtom } from "../../common/brainzplayer/BrainzPlayerAtoms";
import YIMPlaylists, { getPlaylistByName } from "./components/YIMPlaylists";
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
import YIMTopAlbums from "./components/AlbumsCoverflow";
import YIMSimilarUsers from "./components/YIMSimilarUsers";
import { COLOR_LB_BLUE } from "../../utils/constants";

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
const availableYears = {
  2021: {
    color: "red",
    textColor: "#F1F2E1",
    accentColor: COLOR_LB_BLUE,
    backGroundColors: ["#166e30ff", "#3d0a79ff"],
  },
  2022: {
    color: "yellow",
    textColor: "#F1F2E1",
    accentColor: COLOR_LB_BLUE,
    backGroundColors: ["#3d0a79ff", "#158D70"],
  },
  2023: {
    color: "green",
    textColor: "#F1F2E1",
    accentColor: COLOR_LB_BLUE,
    backGroundColors: ["#158D70", "#8C4D89"],
  },
  2024: {
    color: "#158D70",
    textColor: "#F1F2E1",
    accentColor: COLOR_LB_BLUE,
    backGroundColors: ["#8C4D89", "#2f6368"],
  },
  2025: {
    color: "#4E3360",
    textColor: "#F1F2E1",
    accentColor: COLOR_LB_BLUE,
    backGroundColors: ["#2f6368", "#463f62"],
  },
};
export default function YearInMusic() {
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const location = useLocation();
  const params = useParams();
  const { year: yearParam = getYear(Date.now()), userName } = params;
  const [year, setYear] = React.useState<keyof typeof availableYears>(
    Number(yearParam) as keyof typeof availableYears
  );
  const selectedRef = React.useRef<HTMLAnchorElement>(null);

  const { data } = useQuery<YearInMusicLoaderData>(
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

  // Update when viewed user changes
  React.useEffect(() => {
    getFollowing();
  }, [getFollowing, user?.name]);

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

  const {
    accentColor,
    textColor,
    backGroundColors: gradientColors,
  } = availableYears[year];
  const cardBackgroundColor = textColor;
  const backgroundGradient = `linear-gradient(to right, ${gradientColors.join(
    ", "
  )}`;

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

  const handleYearClick = React.useCallback(
    (
      e: React.MouseEvent<HTMLAnchorElement>,
      selectedYear: keyof typeof availableYears
    ) => {
      setYear(selectedYear);

      // This is the magic line that centers the clicked element
      e.currentTarget.scrollIntoView({
        behavior: "smooth",
        inline: "center",
        block: "nearest",
      });
    },
    [setYear]
  );

  React.useEffect(() => {
    if (selectedRef.current) {
      selectedRef.current.scrollIntoView({
        behavior: "auto", // Instant scroll on load
        inline: "center",
        block: "nearest",
      });
    }
  }, []);

  return (
    <div
      id="year-in-music"
      className={`yim-${year}`}
      style={{
        ["--cardBackgroundColor" as any]: cardBackgroundColor,
        ["--accentColor" as any]: accentColor,
        ["--headerColor" as any]: textColor,
        ["--gradientColor1" as any]: gradientColors[0],
        ["--gradientColor2" as any]: gradientColors[1],
      }}
    >
      <div role="main">
        <SEO year={year} userName={user?.name} />
        <YIMYearMetaTags year={year} backgroundColor={backgroundGradient} />
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

          {!hasSomeData && (
            <div className="no-yim-message">
              <p className="center-p">Oh no!</p>
              <p className="center-p">
                We don&apos;t have enough {year} statistics for {user.name}.
              </p>
              <p className="center-p">
                <Link to="/settings/music-services/details/">Submit</Link>{" "}
                enough listens before the end of December to generate your
                #yearinmusic next year.
              </p>
            </div>
          )}
          <div className="arrow-down" />
        </div>
        <div className="year-selection">
          {Object.keys(availableYears).map((availableYear) => {
            const yearAsNum = Number(
              availableYear
            ) as keyof typeof availableYears;
            const isSelectedYear = yearAsNum === year;
            return (
              <Link
                key={availableYear}
                to={`../${availableYear}/`}
                ref={isSelectedYear ? selectedRef : null}
                className={`year-item ${isSelectedYear ? "selected" : ""}`}
                onClick={(e) => handleYearClick(e, yearAsNum)}
              >
                <div className="year-image">
                  <img
                    className="img-fluid"
                    src="/static/img/cover-art-placeholder.jpg"
                    alt={`Cover for year ${availableYear}`}
                  />
                </div>
                <div className="year-separator">
                  <div className="year-connector" />
                  <div className="year-marker" />
                  <div className="year-connector" />
                </div>
                <div className="year-number">{availableYear}</div>
              </Link>
            );
          })}
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
              <div className="content-card" id="overview">
                <h3 className="flex-center">Overview</h3>
                <div className="d-flex justify-content-center">
                  <object
                    className="card"
                    data={`${APIService.APIBaseURI}/art/year-in-music/${year}/${encodedUsername}?image=overview`}
                  >
                    Overview
                  </object>
                </div>
                <div className="yim-share-button-container">
                  <ImageShareButtons
                    svgURL={`${APIService.APIBaseURI}/art/year-in-music/${year}/${encodedUsername}?image=overview`}
                    shareUrl={linkToThisPage}
                    shareText={`Check out my ListenBrainz stats for ${year}`}
                    shareTitle="My year in music"
                    fileName={`${user.name}-overview-${year}`}
                  />
                </div>
              </div>
            </div>

            <YIMTopAlbums
              topReleaseGroups={yearInMusicData.top_release_groups}
              userName={user.name}
              year={year}
            />

            <YIMCharts
              yearInMusicData={yearInMusicData}
              userName={user.name}
              year={year}
            />

            <div className="section" id="stats">
              <div className="content-card">
                <h3 className="flex-center">{year} statistics</h3>
                <YIMStats
                  yearInMusicData={yearInMusicData}
                  userName={user.name}
                />
                <YIMListeningActivity
                  listensPerDay={yearInMusicData.listens_per_day}
                  userName={user.name}
                  year={year}
                />
                <YIMMostListenedYear
                  mostListenedYearData={yearInMusicData.most_listened_year}
                  userName={user.name}
                />
                <YIMArtistMap
                  artistMapData={yearInMusicData.artist_map}
                  yourOrUsersName={yourOrUsersName}
                />
                {genreGraphData && (
                  <YIMGenreGraph
                    genreGraphData={genreGraphData}
                    userName={user.name}
                  />
                )}
                <div className="yim-share-button-container">
                  <ImageShareButtons
                    svgURL={`${APIService.APIBaseURI}/art/year-in-music/${year}/${encodedUsername}?image=stats`}
                    shareUrl={`${linkToThisPage}#stats`}
                    shareTitle={`My music listening in ${year}`}
                    fileName={`${user.name}-stats-${year}`}
                  />
                </div>
              </div>
            </div>

            <YIMPlaylists
              yearInMusicData={yearInMusicData}
              year={year}
              userName={user.name}
            />
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

        <YIMFriends
          followingList={followingList}
          userName={user.name}
          year={year}
        />

        {/* ADD Community Year in Music tools ♡HERE */}

        <div className="section">
          {userShareBar}
          <div className="closing-remarks align-items-center flex flex-column gap-5">
            <img src="/static/img/year-in-music/heart.png" alt="With love," />
            <img
              src="/static/img/year-in-music/listenbrainz-footer.png"
              alt="The ListenBrainz team"
            />
            <p className="bold">
              Wishing you a very cozy {year + 1}, from the ListenBrainz team.
            </p>
            <p>
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
            <img
              src="/static/img/year-in-music/OSS-footer.png"
              alt="Open source and ethical forever"
            />
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
