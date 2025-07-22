/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as _ from "lodash";
import * as React from "react";

import NiceModal from "@ebay/nice-modal-react";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCalendar } from "@fortawesome/free-regular-svg-icons";
import {
  faCompactDisc,
  faTrashAlt,
  faRss,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { cloneDeep, get, isEmpty, isEqual, isNil } from "lodash";
import DateTimePicker from "react-datetime-picker/dist/entry.nostyle";
import { toast } from "react-toastify";
import { io } from "socket.io-client";
import { Link, useLocation, useParams, useSearchParams } from "react-router";
import { Helmet } from "react-helmet";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSetAtom } from "jotai";
import GlobalAppContext from "../utils/GlobalAppContext";

import AddListenModal from "./components/AddListenModal";
import UserSocialNetwork from "./components/follow/UserSocialNetwork";
import ListenCard from "../common/listens/ListenCard";
import ListenControl from "../common/listens/ListenControl";
import ListenCountCard from "../common/listens/ListenCountCard";
import { ToastMsg } from "../notifications/Notifications";
import PinnedRecordingCard from "./components/PinnedRecordingCard";
import {
  formatWSMessageToListen,
  getBaseUrl,
  getListenablePin,
  getListenCardKey,
  getObjectForURLSearchParams,
  getRecordingMSID,
} from "../utils/utils";
import FollowButton from "./components/follow/FollowButton";
import { RouteQuery } from "../utils/Loader";
import ReportUserButton from "../report-user/ReportUser";
import SyndicationFeedModal from "../components/SyndicationFeedModal";
import { setAmbientQueueAtom } from "../common/brainzplayer/BrainzPlayerAtoms";

export type ListensProps = {
  latestListenTs: number;
  listens?: Array<Listen>;
  oldestListenTs: number;
  user: ListenBrainzUser;
  userPinnedRecording?: PinnedRecording;
  playingNow?: Listen;
  already_reported_user: boolean;
};

type ListenLoaderData = ListensProps;

export default function Listen() {
  const location = useLocation();
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsObject = getObjectForURLSearchParams(searchParams);
  const isTimeNavigation =
    _.has(searchParamsObject, "max_ts") || _.has(searchParamsObject, "min_ts");

  const { queryKey, queryFn } = RouteQuery(
    ["dashboard", params, searchParamsObject],
    location.pathname
  );

  const { data, refetch } = useQuery<ListenLoaderData>({
    queryKey,
    queryFn,
    staleTime: isTimeNavigation ? 1000 * 60 * 5 : 0,
  });

  const {
    listens = [],
    user,
    userPinnedRecording = undefined,
    playingNow = undefined,
    latestListenTs = 0,
    oldestListenTs = 0,
    already_reported_user = false,
  } = data || {};

  const previousListenTs = listens[0]?.listened_at;
  const nextListenTs = listens[listens.length - 1]?.listened_at;

  const { currentUser, websocketsUrl, APIService } = React.useContext(
    GlobalAppContext
  );

  const expectedListensPerPage = 25;
  const maxWebsocketListens = 7;

  const listensTable = React.createRef<HTMLTableElement>();
  const [webSocketListens, setWebSocketListens] = React.useState<Array<Listen>>(
    []
  );
  const [followingList, setFollowingList] = React.useState<Array<string>>([]);

  const [deletedListen, setDeletedListen] = React.useState<Listen | null>(null);
  const [listenCount, setListenCount] = React.useState<number | undefined>();
  const [dateTimePickerValue, setDateTimePickerValue] = React.useState<Date>(
    nextListenTs ? new Date(nextListenTs * 1000) : new Date(Date.now())
  );

  const queryClient = useQueryClient();

  const receiveNewListen = React.useCallback(
    (newListen: string): void => {
      let json;
      try {
        json = JSON.parse(newListen);
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Couldn't parse the new listen as JSON: "
            message={error?.toString()}
          />,
          { toastId: "parse-listen-error" }
        );
        return;
      }
      const listen = formatWSMessageToListen(json);

      if (listen) {
        setWebSocketListens((prevWebSocketListens) => {
          return [
            listen,
            ..._.take(prevWebSocketListens, maxWebsocketListens - 1),
          ];
        });
      }
    },
    [setWebSocketListens]
  );

  const receiveNewPlayingNow = React.useCallback(
    async (receivedPlayingNow: Listen): Promise<Listen> => {
      let newPlayingNow = receivedPlayingNow;
      try {
        const response = await APIService.lookupRecordingMetadata(
          newPlayingNow.track_metadata.track_name,
          newPlayingNow.track_metadata.artist_name,
          true
        );
        if (response) {
          const {
            metadata,
            recording_mbid,
            release_mbid,
            artist_mbids,
          } = response;
          // ListenCard does not deepcopy the listen passed to it in props, therefore modifying the object here would
          // change the object stored inside ListenCard's state even before react can propagate updates. therefore, clone
          // first
          newPlayingNow = cloneDeep(newPlayingNow);
          newPlayingNow.track_metadata.mbid_mapping = {
            recording_mbid,
            release_mbid,
            artist_mbids,
            caa_id: metadata?.release?.caa_id,
            caa_release_mbid: metadata?.release?.caa_release_mbid,
            artists: metadata?.artist?.artists?.map((artist, index) => {
              return {
                artist_credit_name: artist.name,
                join_phrase: artist.join_phrase ?? "",
                artist_mbid: artist_mbids[index],
              };
            }),
          };
        }
      } catch (error) {
        toast.error(
          <ToastMsg
            title="We could not load data for the now playing listen "
            message={
              typeof error === "object" ? error.message : error.toString()
            }
          />,
          { toastId: "load-listen-error" }
        );
      }
      return newPlayingNow;
    },
    [APIService]
  );

  const getFollowing = React.useCallback(async () => {
    const { getFollowingForUser } = APIService;
    if (!currentUser?.name) {
      return;
    }
    try {
      const response = await getFollowingForUser(currentUser.name);
      const { following } = response;

      setFollowingList(following);
    } catch (err) {
      toast.error(
        <ToastMsg
          title="Error while fetching following"
          message={err.toString()}
        />,
        { toastId: "fetch-following-error" }
      );
    }
  }, [APIService, currentUser?.name]);

  React.useEffect(() => {
    if (user?.name) {
      APIService.getUserListenCount(user.name)
        .then((listenCountValue) => {
          setListenCount(listenCountValue);
        })
        .catch((error) => {
          toast.error(
            <ToastMsg
              title="Sorry, we couldn't load your listens count…"
              message={error?.toString()}
            />,
            { toastId: "listen-count-error" }
          );
        });
    }
    // Navigated to another user's dashboard, reset WS listens
    setWebSocketListens([]);
  }, [APIService, user?.name]);

  React.useEffect(() => {
    getFollowing();
  }, [currentUser, getFollowing]);

  const { mutate: updatePlayingNowMutation } = useMutation({
    mutationFn: receiveNewPlayingNow,
    onSuccess: (newPlayingNowListen) => {
      queryClient.setQueryData(queryKey, (oldData: ListenLoaderData) => {
        return {
          ...oldData,
          playingNow: newPlayingNowListen,
        };
      });
    },
  });

  React.useEffect(() => {
    // On first load, run the function to load the metadata for the playing_now listen
    if (playingNow) updatePlayingNowMutation(playingNow);
    // no exhaustive-deps because we only want to run this on initial start
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    // if modifying the uri or path, lookup socket.io namespace vs paths.
    // tl;dr io("https://listenbrainz.org/socket.io/") and
    // io("https://listenbrainz.org", { path: "/socket.io" }); are not equivalent
    const socket = io(websocketsUrl || window.location.origin, {
      path: "/socket.io/",
    });

    const connectHandler = () => {
      if (user?.name) {
        socket.emit("json", { user: user.name });
      }
    };
    const newListenHandler = (socketData: string) => {
      receiveNewListen(socketData);
    };
    const newPlayingNowHandler = (socketData: string) => {
      const newPlayingNow = JSON.parse(socketData) as Listen;
      updatePlayingNowMutation(newPlayingNow);
    };

    socket.on("connect", connectHandler);
    socket.on("listen", newListenHandler);
    socket.on("playing_now", newPlayingNowHandler);

    return () => {
      socket.off("connect", connectHandler);
      socket.off("listen", newListenHandler);
      socket.off("playing_now", newPlayingNowHandler);
      socket.close();
    };
  }, [receiveNewListen, updatePlayingNowMutation, user?.name, websocketsUrl]);

  const updateFollowingList = (
    follower: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => {
    const newFollowingList = [...followingList];
    const index = newFollowingList.findIndex(
      (following) => following === follower.name
    );
    if (action === "follow" && index === -1) {
      newFollowingList.push(follower.name);
    }
    if (action === "unfollow" && index !== -1) {
      newFollowingList.splice(index, 1);
    }
    setFollowingList(newFollowingList);
  };

  const loggedInUserFollowsUser = (): boolean => {
    if (_.isNil(currentUser) || _.isEmpty(currentUser) || !user) {
      return false;
    }

    return followingList.includes(user.name);
  };

  const deleteListen = React.useCallback(
    async (listen: Listen) => {
      const isCurrentUser =
        Boolean(listen.user_name) && listen.user_name === currentUser?.name;
      if (isCurrentUser && currentUser?.auth_token) {
        const listenedAt = get(listen, "listened_at");
        const recordingMsid = getRecordingMSID(listen);

        try {
          const status = await APIService.deleteListen(
            currentUser.auth_token,
            recordingMsid,
            listenedAt
          );
          if (status === 200) {
            setDeletedListen(listen);
            toast.info(
              <ToastMsg
                title="Success"
                message={
                  "This listen has not been deleted yet, but is scheduled for deletion, " +
                  "which usually happens shortly after the hour."
                }
              />,
              { toastId: "delete-listen" }
            );
            // wait for the delete animation to finish
            await new Promise((resolve) => {
              setTimeout(resolve, 1000);
            });
            return listen;
          }
        } catch (error) {
          toast.error(
            <ToastMsg
              title="Error while deleting listen"
              message={
                typeof error === "object" ? error.message : error.toString()
              }
            />,
            { toastId: "delete-listen-error" }
          );
        }
      }
      return undefined;
    },
    [APIService, currentUser]
  );
  const { mutate: deleteListenMutation } = useMutation({
    mutationFn: deleteListen,
    onSuccess: (newlyDeletedListen) => {
      queryClient.setQueryData<ListenLoaderData>(queryKey, (oldData) => {
        if (!oldData?.listens || !newlyDeletedListen) {
          return oldData;
        }
        return {
          ...oldData,
          listens: _.without(oldData.listens, newlyDeletedListen),
        };
      });
    },
  });

  const getListenCard = React.useCallback(
    (listen: Listen): JSX.Element => {
      const isCurrentUser =
        Boolean(listen.user_name) && listen.user_name === currentUser?.name;
      const listenedAt = get(listen, "listened_at");
      const recordingMSID = getRecordingMSID(listen);
      const canDelete =
        isCurrentUser &&
        (Boolean(listenedAt) || listenedAt === 0) &&
        Boolean(recordingMSID);

      const additionalMenuItems = [];

      if (canDelete) {
        additionalMenuItems.push(
          <ListenControl
            text="Delete Listen"
            key="Delete Listen"
            icon={faTrashAlt}
            action={() => deleteListenMutation(listen)}
          />
        );
      }
      const shouldBeDeleted = isEqual(deletedListen, listen);
      return (
        <ListenCard
          key={getListenCardKey(listen)}
          showTimestamp
          showUsername={false}
          listen={listen}
          className={`${listen.playing_now ? "playing-now " : ""}${
            shouldBeDeleted ? "deleted " : ""
          }`}
          additionalMenuItems={additionalMenuItems}
        />
      );
    },
    [currentUser?.name, deletedListen, deleteListenMutation]
  );

  const onChangeDateTimePicker = async (newDateTimePickerValue: Date) => {
    if (!newDateTimePickerValue) {
      return;
    }
    setDateTimePickerValue(newDateTimePickerValue);
    let minJSTimestamp;
    if (Array.isArray(newDateTimePickerValue)) {
      // Range of dates
      minJSTimestamp = newDateTimePickerValue[0].getTime();
    } else {
      minJSTimestamp = newDateTimePickerValue.getTime();
    }

    // Constrain to oldest listen TS for that user
    const minTimestampInSeconds = Math.max(
      // convert JS time (milliseconds) to seconds
      Math.round(minJSTimestamp / 1000),
      oldestListenTs
    );

    setSearchParams({ min_ts: minTimestampInSeconds.toString() });
  };

  let allListenables = listens;
  if (userPinnedRecording) {
    const listenablePin = getListenablePin(userPinnedRecording);
    allListenables = [listenablePin, ...listens];
  }

  const setAmbientQueue = useSetAtom(setAmbientQueueAtom);

  React.useEffect(() => {
    setAmbientQueue(allListenables);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allListenables]);

  const isNewestButtonDisabled = listens[0]?.listened_at >= latestListenTs;
  const isNewerButtonDisabled =
    !previousListenTs || previousListenTs >= latestListenTs;
  const isOlderButtonDisabled = !nextListenTs || nextListenTs <= oldestListenTs;
  const isOldestButtonDisabled =
    listens.length > 0 &&
    listens[listens.length - 1]?.listened_at <= oldestListenTs;
  const isUserLoggedIn = !isNil(currentUser) && !isEmpty(currentUser);
  const isCurrentUsersPage = currentUser?.name === user?.name;

  return (
    <div role="main" id="dashboard">
      <Helmet>
        <title>{`${
          user?.name === currentUser?.name ? "Your" : `${user?.name}'s`
        } Listens`}</title>
      </Helmet>
      <div className="row">
        <div className="col-lg-4 order-lg-2 side-column">
          <div className="listen-header">
            {isUserLoggedIn && !isCurrentUsersPage && user && (
              <FollowButton
                type="icon-only"
                user={user}
                loggedInUserFollowsUser={loggedInUserFollowsUser()}
                updateFollowingList={updateFollowingList}
              />
            )}
            <Link
              to={`https://musicbrainz.org/user/${user?.name}`}
              className="btn btn-info musicbrainz-profile-button"
            >
              <img
                src="/static/img/musicbrainz-16.svg"
                alt="MusicBrainz Logo"
              />{" "}
              MusicBrainz
            </Link>
            {user && !isCurrentUsersPage && (
              <ReportUserButton
                user={user}
                alreadyReported={already_reported_user}
              />
            )}
          </div>
          {playingNow && getListenCard(playingNow)}
          {userPinnedRecording && (
            <PinnedRecordingCard
              pinnedRecording={userPinnedRecording}
              isCurrentUser={isCurrentUsersPage}
              removePinFromPinsList={() => {}}
            />
          )}
          {user && <ListenCountCard user={user} listenCount={listenCount} />}
          {user && <UserSocialNetwork user={user} />}
        </div>
        <div className="col-lg-8 order-lg-1">
          {!listens.length && (
            <div className="empty-listens">
              <FontAwesomeIcon icon={faCompactDisc as IconProp} size="10x" />
              {isCurrentUsersPage ? (
                <div className="lead empty-text">Get listening</div>
              ) : (
                <div className="lead empty-text">
                  {user?.name} hasn&apos;t listened to any songs yet.
                </div>
              )}

              {isCurrentUsersPage && (
                <div className="empty-action">
                  Import{" "}
                  <Link to="/settings/import/">your listening history</Link>{" "}
                  from last.fm/libre.fm and track your listens by{" "}
                  <Link to="/settings/music-services/details/">
                    connecting to a music streaming service
                  </Link>
                  , or use{" "}
                  <Link to="/add-data/">one of these music players</Link> to
                  start submitting your listens.
                </div>
              )}
            </div>
          )}
          {webSocketListens.length > 0 && (
            <div className="webSocket-box">
              <h4>New listens since you arrived</h4>
              <div id="webSocketListens" data-testid="webSocketListens">
                {webSocketListens.map((listen) => getListenCard(listen))}
              </div>
              <div className="read-more">
                <button
                  type="button"
                  className="btn btn-outline-info"
                  onClick={() => {
                    refetch();
                    setWebSocketListens([]);
                  }}
                >
                  See more fresh listens
                </button>
              </div>
            </div>
          )}
          <div className="listen-header">
            {listens.length === 0 ? (
              <div id="spacer" />
            ) : (
              <h3 className="header-with-line">Recent listens</h3>
            )}
            {isCurrentUsersPage && (
              <div className="dropdown add-listen-btn">
                <button
                  className="btn btn-info dropdown-toggle"
                  type="button"
                  id="addListensDropdown"
                  data-bs-toggle="dropdown"
                  aria-haspopup="true"
                >
                  Add listens&nbsp;
                  <span className="caret" />
                </button>
                <ul
                  className="dropdown-menu dropdown-menu-right"
                  aria-labelledby="addListensDropdown"
                >
                  <button
                    type="button"
                    onClick={() => {
                      NiceModal.show(AddListenModal);
                    }}
                    className="dropdown-item"
                  >
                    Manual addition
                  </button>
                  <Link
                    to="/settings/music-services/details/"
                    className="dropdown-item"
                  >
                    Connect music services
                  </Link>
                  <Link to="/settings/import/" className="dropdown-item">
                    Import your listens
                  </Link>
                  <Link to="/add-data/" className="dropdown-item">
                    Submit from music players
                  </Link>
                  <Link to="/settings/link-listens/" className="dropdown-item">
                    Link unmatched listens
                  </Link>
                </ul>
              </div>
            )}
            <button
              type="button"
              className="btn btn-icon btn-info atom-button"
              title="Subscribe to syndication feed (Atom)"
              onClick={() => {
                NiceModal.show(SyndicationFeedModal, {
                  feedTitle: "Recent listens",
                  options: [
                    {
                      label: "Time range",
                      key: "minutes",
                      type: "dropdown",
                      tooltip:
                        "Select the time range for the feed. For instance, choosing '30 minutes' will include listens from the last 30 minutes. It's recommended to set your feed reader's refresh interval to match this time range for optimal updates.",
                      values: [
                        {
                          id: "10minutes",
                          value: "10",
                          displayValue: "10 minutes",
                        },
                        {
                          id: "30minutes",
                          value: "30",
                          displayValue: "30 minutes",
                        },
                        {
                          id: "1hour",
                          value: "60",
                          displayValue: "1 hour",
                        },
                        {
                          id: "2hours",
                          value: "120",
                          displayValue: "2 hours",
                        },
                        {
                          id: "4hours",
                          value: "240",
                          displayValue: "4 hours",
                        },
                        {
                          id: "8hours",
                          value: "480",
                          displayValue: "8 hours",
                        },
                      ],
                    },
                  ],
                  baseUrl: `${getBaseUrl()}/syndication-feed/user/${
                    user?.name
                  }/listens`,
                });
              }}
            >
              <FontAwesomeIcon icon={faRss} size="sm" />
            </button>
          </div>

          {listens.length > 0 && (
            <div>
              <div
                id="listens"
                data-testid="listens"
                ref={listensTable}
                style={{ opacity: "1" }}
              >
                {listens.map(getListenCard)}
              </div>
              {listens.length < expectedListensPerPage && (
                <h5 className="text-center">No more listens to show</h5>
              )}
              <ul className="pagination" id="navigation">
                <li
                  className={`page-item ${
                    isNewestButtonDisabled ? "disabled" : ""
                  }`}
                >
                  <Link
                    role="button"
                    aria-label="Navigate to most recent listens"
                    tabIndex={0}
                    aria-disabled={isNewestButtonDisabled}
                    to={location.pathname}
                    className="page-link"
                  >
                    &#x21E4;
                  </Link>
                </li>
                <li
                  className={`page-item me-auto ${
                    isNewerButtonDisabled ? "disabled" : ""
                  }`}
                >
                  <Link
                    role="button"
                    aria-label="Navigate to more recent listens"
                    tabIndex={0}
                    aria-disabled={isNewerButtonDisabled}
                    to={`?min_ts=${previousListenTs}`}
                    className="page-link"
                  >
                    &larr; Newer
                  </Link>
                </li>
                <li className="feed-button-and-date-time-picker mx-auto">
                  <DateTimePicker
                    onChange={onChangeDateTimePicker}
                    value={dateTimePickerValue}
                    clearIcon={null}
                    maxDate={new Date(Date.now())}
                    minDate={
                      oldestListenTs
                        ? new Date(oldestListenTs * 1000)
                        : undefined
                    }
                    calendarIcon={
                      <FontAwesomeIcon icon={faCalendar as IconProp} />
                    }
                    format="yyyy-MM-dd"
                    disableClock
                  />
                </li>
                <li
                  className={`page-item ms-auto ${
                    isOlderButtonDisabled ? "disabled" : ""
                  }`}
                  style={{ marginLeft: "auto" }}
                >
                  <Link
                    aria-label="Navigate to older listens"
                    type="button"
                    aria-disabled={isOlderButtonDisabled}
                    tabIndex={0}
                    to={`?max_ts=${nextListenTs}`}
                    className="page-link"
                  >
                    Older &rarr;
                  </Link>
                </li>
                <li
                  className={`page-item next ${
                    isOldestButtonDisabled ? "disabled" : ""
                  }`}
                >
                  <Link
                    aria-label="Navigate to oldest listens"
                    role="button"
                    tabIndex={0}
                    aria-disabled={isOldestButtonDisabled}
                    to={`?min_ts=${oldestListenTs - 1}`}
                    className="page-link"
                  >
                    &#x21E5;
                  </Link>
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
