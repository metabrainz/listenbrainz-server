import React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import Tooltip from "react-tooltip";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { getEntityLink } from "../../stats/utils";
import { getArtistLink } from "../../../utils/utils";
import ListenCard from "../../../common/listens/ListenCard";

export type YIMNewReleasesData = Array<{
  title: string;
  release_group_mbid: string;
  caa_id?: number;
  caa_release_mbid?: string;
  artist_credit_mbids: string[];
  artist_credit_name: string;
  artists?: Array<MBIDMappingArtist>;
}>;
type YIMNewReleasesProps = {
  newReleases: YIMNewReleasesData;
  userName: string;
  year: number;
};
export default function YIMNewReleases({
  newReleases,
  userName,
  year,
}: YIMNewReleasesProps) {
  const { currentUser } = React.useContext(GlobalAppContext);
  if (!newReleases || newReleases.length === 0) {
    return null;
  }
  const isCurrentUser = userName === currentUser?.name;
  const youOrUsername = isCurrentUser ? "you" : `${userName}`;
  const yourOrUsersName = isCurrentUser ? "your" : `${userName}'s`;
  return (
    <div
      className="content-card"
      id="new-releases"
      style={{ marginBottom: "2.5em" }}
    >
      <div className="heading">
        <h3>
          New albums from {yourOrUsersName} top artists{" "}
          <FontAwesomeIcon
            icon={faQuestionCircle}
            data-tip
            data-for="new-albums-helptext"
            size="xs"
          />
          <Tooltip id="new-albums-helptext">
            Albums and singles released in {year} from artists {youOrUsername}{" "}
            listened to.
            <br />
            Missed anything?
          </Tooltip>
        </h3>
      </div>
      <div className="scrollable-area card-bg">
        {newReleases.map((release) => {
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
              <div title={release.title} className="ellipsis-2-lines">
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
        })}
      </div>
    </div>
  );
}
