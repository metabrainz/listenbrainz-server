import * as React from "react";

import {
  faBorderAll,
  faGlobe,
  faInfoCircle,
  faUser,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  Link,
  useLoaderData,
  useNavigate,
  useSearchParams,
} from "react-router";
import { Helmet } from "react-helmet";

import Tooltip from "react-tooltip";
import NiceModal from "@ebay/nice-modal-react";
import { Card } from "react-bootstrap";
import Pill from "../../components/Pill";
import UserListeningActivity from "./components/UserListeningActivity";
import UserTopEntity from "./components/UserTopEntity";
import UserDailyActivity from "./components/UserDailyActivity";
import UserArtistMap from "./components/UserArtistMap";
import UserArtistActivity from "./components/UserArtistActivity";
import UserEraActivity from "./components/UserEraActivity";
import UserGenreActivity from "./components/UserGenreActivity";
import { getAllStatRanges, isInvalidStatRange } from "./utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import StatsExplanationsModal from "../../common/stats/StatsExplanationsModal";

export type UserReportsProps = {
  user?: ListenBrainzUser;
};

export type UserReportsState = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
};

export default function UserReports() {
  const props = useLoaderData() as UserReportsProps;
  const { user = undefined } = props ?? {};

  // Context
  const { currentUser, APIService } = React.useContext(GlobalAppContext);

  // Router
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const range = searchParams.get("range") as UserStatsAPIRange;

  React.useEffect(() => {
    if (!range || isInvalidStatRange(range)) {
      setSearchParams({ range: "week" }, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range]);

  if (!range || isInvalidStatRange(range)) {
    return null;
  }

  const handleRangeChange = (newRange: UserStatsAPIRange) => {
    setSearchParams({ range: newRange });
  };

  const ranges = getAllStatRanges();
  const userOrLoggedInUser: string | undefined =
    user?.name ?? currentUser?.name;

  const userStatsTitle =
    user?.name === currentUser?.name ? "Your" : `${userOrLoggedInUser}'s`;

  const statsExplanationModalButton = (
    <button
      type="button"
      className="btn btn-link"
      onClick={() => {
        NiceModal.show(StatsExplanationsModal);
      }}
    >
      <FontAwesomeIcon icon={faInfoCircle} style={{ marginRight: "0.5rem" }} />
      How and when are statistics calculated?
    </button>
  );

  const encodedUserOrCurrentUserName = user?.name
    ? encodeURIComponent(user.name)
    : encodeURIComponent(currentUser.name);
  let albumStatsUrl = "";
  if (user) {
    albumStatsUrl = `/user/${encodeURIComponent(user.name)}/stats`;
  } else {
    albumStatsUrl = `/statistics`;
  }
  albumStatsUrl += `/top-albums/?range=${range}`;
  return (
    <div data-testid="User Reports">
      <Helmet>
        <title>{userOrLoggedInUser ? userStatsTitle : "Sitewide"} Stats</title>
      </Helmet>
      <div className="tertiary-nav dragscroll">
        <div>
          {Array.from(ranges, ([stat_type, stat_name]) => {
            return (
              <Pill
                key={`${stat_type}-${stat_name}`}
                active={range === stat_type}
                type="secondary"
                onClick={() => handleRangeChange(stat_type)}
                data-testid={`range-${stat_type}`}
              >
                {stat_name}
              </Pill>
            );
          })}
        </div>
        <div>
          {Boolean(userOrLoggedInUser) && (
            <button
              type="button"
              onClick={() => {
                navigate(
                  `/user/${encodedUserOrCurrentUserName}/stats/?range=${range}`
                );
              }}
              className={`pill secondary ${user ? "active" : ""}`}
            >
              <FontAwesomeIcon icon={faUser} />{" "}
              {user?.name ?? currentUser?.name}
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              navigate(`/statistics/?range=${range}`);
            }}
            className={`pill secondary ${!user ? "active" : ""}`}
          >
            <FontAwesomeIcon icon={faGlobe} /> Global
          </button>
        </div>
      </div>
      <section id="listening-activity">
        {statsExplanationModalButton}
        <div className="row d-flex">
          <div className="col-md-8">
            <UserListeningActivity range={range} user={user} />
          </div>
          <div className="col-md-4 flex">
            <Card className="flex-center" data-testid="top-release-group">
              <object
                className="p-4 m-auto"
                width="100%"
                style={{
                  maxWidth: "600px",
                  width: "-webkit-fill-available",
                }}
                aria-label="Album cover grid"
                data={`${APIService.APIBaseURI}/art/grid-stats/${encodedUserOrCurrentUserName}/${range}/5/1/600`}
              />
              <Link
                to="/explore/art-creator/"
                className="mb-4 btn btn-info"
                style={
                  { "--bs-btn-border-radius": "0.5rem" } as React.CSSProperties
                }
              >
                Visualize & share{" "}
                <FontAwesomeIcon icon={faBorderAll} size="lg" />
              </Link>
            </Card>
          </div>
        </div>
      </section>
      <section id="top-entity">
        {statsExplanationModalButton}
        <div className="row">
          <div className="col-md-4">
            <UserTopEntity
              range={range}
              entity="artist"
              user={user}
              terminology="artist"
            />
          </div>
          <div className="col-md-4">
            <UserTopEntity
              range={range}
              entity="release-group"
              user={user}
              terminology="album"
              extraButtons={[
                <Link
                  to="/explore/art-creator/"
                  className="btn btn-info"
                  style={
                    {
                      "--bs-btn-border-radius": "0.5rem",
                    } as React.CSSProperties
                  }
                >
                  Visualize & share{" "}
                  <FontAwesomeIcon icon={faBorderAll} size="lg" />
                </Link>,
              ]}
            />
          </div>
          <div className="col-md-4">
            <UserTopEntity
              range={range}
              entity="recording"
              user={user}
              terminology="track"
            />
          </div>
        </div>
      </section>
      {user && (
        <section id="daily-activity">
          {statsExplanationModalButton}
          <UserDailyActivity range={range} user={user} />
        </section>
      )}
      <section id="artist-activity">
        {statsExplanationModalButton}
        <UserArtistActivity range={range} user={user} />
      </section>
      <section id="era-activity">
        {statsExplanationModalButton}
        <UserEraActivity range={range} user={user} />
      </section>
      {user && (
        <section id="genre-activity">
          {statsExplanationModalButton}
          <UserGenreActivity range={range} user={user} />
        </section>
      )}
      <section id="artist-origin">
        {statsExplanationModalButton}
        <UserArtistMap range={range} user={user} />
      </section>
    </div>
  );
}
